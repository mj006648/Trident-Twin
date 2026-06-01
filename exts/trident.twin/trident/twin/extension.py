"""Trident Twin Isaac Sim extension — live Lakehouse binding.

Polls twin-hub /api/twin/entities using Kit's update loop (no threading).

동작:
  - ingest 중인 namespace마다 컨베이어 벨트 위에 상자 prim 생성
  - 각 게이트(INGEST/STRUCT/INDEX/EMBED/AUDIT) 완료 시 해당 뱃지를 상자에 attach
  - 상자는 완료된 마지막 게이트 다음 위치로 이동
  - AUDIT 완료 시 Lakehouse 방향으로 이동 후 제거

Environment variables:
  TWIN_HUB_URL         twin-hub base URL (default: http://localhost:8765)
  TWIN_POLL_INTERVAL   poll cadence in seconds (default: 5)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
from pxr import Gf, Sdf, UsdGeom

DEFAULT_TWIN_HUB_URL  = "http://localhost:8765"
DEFAULT_POLL_INTERVAL = 5.0

# 게이트 순서: (step_no, operation_id, 뱃지 색 RGB, 컨베이어 X 위치)
GATES = [
    (1, "s3_raw_ingestion",    Gf.Vec3f(0.80, 0.50, 0.10),  7.0),   # bronze
    (2, "iceberg_structurize", Gf.Vec3f(0.40, 0.65, 0.95),  10.0),  # schema blue
    (3, "search_index_build",  Gf.Vec3f(0.20, 0.80, 0.35),  13.0),  # quality green
    (4, "milvus_redis_indexing",Gf.Vec3f(0.75, 0.30, 0.90), 16.0),  # semantic purple
    (5, "integrity_audit",     Gf.Vec3f(0.95, 0.75, 0.05),  19.0),  # audit gold
]

BELT_Y      =  -0.7    # main belt Y center
BELT_Z_TOP  =   0.70   # belt surface Z
BOX_SIDE    =   0.40   # 상자 한 변 길이
BOX_Z       =   BELT_Z_TOP + BOX_SIDE / 2
BADGE_SIDE  =   0.12
BADGE_Z_OFF =   BOX_SIDE / 2 + BADGE_SIDE / 2 + 0.02
LAKEHOUSE_X =   23.0   # AUDIT 완료 후 이동할 X

# namespace별 상자 상태
# { ns: { "box_path": str, "badges": int (완료 게이트 수) } }
_box_state: dict[str, dict[str, Any]] = {}


def _env_float(key: str, default: float) -> float:
    try:
        return float(os.environ.get(key, default))
    except ValueError:
        return default


# ── USD 헬퍼 ─────────────────────────────────────────────────────────────────

def _set_display_color(prim, color: Gf.Vec3f) -> None:
    gprim = UsdGeom.Gprim(prim)
    if not gprim:
        return
    attr = gprim.GetDisplayColorAttr()
    if not attr:
        attr = gprim.CreateDisplayColorAttr()
    attr.Set([color])


def _set_translate(prim, x: float, y: float, z: float) -> None:
    xform = UsdGeom.Xformable(prim)
    ops = xform.GetOrderedXformOps()
    for op in ops:
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            op.Set(Gf.Vec3d(x, y, z))
            return
    xform.AddTranslateOp().Set(Gf.Vec3d(x, y, z))


def _ensure_scope(stage, path: str) -> None:
    if not stage.GetPrimAtPath(path).IsValid():
        UsdGeom.Scope.Define(stage, path)


# ── 상자 생성/이동/제거 ───────────────────────────────────────────────────────

def _make_box(stage, path: str, x: float) -> None:
    """컨베이어 위에 상자 prim 생성."""
    xform = UsdGeom.Xform.Define(stage, path)
    xform.AddTranslateOp().Set(Gf.Vec3d(x, BELT_Y, BOX_Z))
    xform.AddScaleOp().Set(Gf.Vec3f(BOX_SIDE, BOX_SIDE, BOX_SIDE))
    body = UsdGeom.Cube.Define(stage, f"{path}/Body")
    _set_display_color(body.GetPrim(), Gf.Vec3f(0.85, 0.85, 0.85))  # 밝은 회색


def _move_box(stage, path: str, x: float) -> None:
    prim = stage.GetPrimAtPath(path)
    if not prim.IsValid():
        return
    _set_translate(prim, x, BELT_Y, BOX_Z)


def _add_badge(stage, box_path: str, badge_no: int, color: Gf.Vec3f) -> None:
    """상자 위에 뱃지 cube를 순서대로 붙임 (badge_no: 1-based)."""
    badge_path = f"{box_path}/Badge_{badge_no:02d}"
    if stage.GetPrimAtPath(badge_path).IsValid():
        return
    badge_x = (badge_no - 3) * (BADGE_SIDE + 0.02)   # 상자 중앙 기준 X 오프셋
    xform = UsdGeom.Xform.Define(stage, badge_path)
    xform.AddTranslateOp().Set(Gf.Vec3d(badge_x, 0.0, BADGE_Z_OFF))
    xform.AddScaleOp().Set(Gf.Vec3f(BADGE_SIDE, BADGE_SIDE, BADGE_SIDE))
    cube = UsdGeom.Cube.Define(stage, f"{badge_path}/Body")
    _set_display_color(cube.GetPrim(), color)


def _remove_box(stage, path: str) -> None:
    prim = stage.GetPrimAtPath(path)
    if prim.IsValid():
        stage.RemovePrim(prim.GetPath())


# ── twin-hub 폴링 ─────────────────────────────────────────────────────────────

def _fetch_entities(base_url: str) -> list[dict] | None:
    try:
        req = urllib.request.Request(base_url.rstrip("/") + "/api/twin/entities")
        with urllib.request.urlopen(req, timeout=4.0) as r:
            data = json.loads(r.read().decode("utf-8"))
            return data.get("entities", [])
    except Exception as e:
        carb.log_warn(f"[trident.twin] fetch failed: {e}")
        return None


# ── 핵심 로직 ─────────────────────────────────────────────────────────────────

def _extract_gate_statuses(entities: list[dict]) -> dict[int, str]:
    """operation entity에서 게이트별 status 추출."""
    result: dict[int, str] = {}
    for e in entities:
        if e.get("type") != "pipeline_operation":
            continue
        no = e.get("step_no")
        if no is not None:
            result[int(no)] = e.get("status", "pending")
    return result


def _extract_active_namespaces(entities: list[dict]) -> dict[str, str]:
    """raw_bucket entity에서 현재 활성 namespace → status 추출.

    s3_file_count > 0 이거나 index_row_count > 0 인 namespace만 대상으로 한다.
    status == "ok" / "PASS" 는 완료된 것이므로 제외 (상자 제거 대상).
    """
    result: dict[str, str] = {}
    for e in entities:
        if e.get("type") != "raw_bucket":
            continue
        ns = e.get("namespace")
        if not ns:
            continue
        status = e.get("status", "pending")
        # 완료된 namespace는 active에서 제외 → _sync_boxes에서 상자 제거됨
        if status in ("ok", "PASS", "done"):
            continue
        # 파일이 하나도 없으면 아직 업로드 안 된 것 — 표시 안 함
        s3 = int(e.get("s3_file_count") or 0)
        idx = int(e.get("index_row_count") or 0)
        if s3 == 0 and idx == 0:
            continue
        result[ns] = status
    return result


def _box_x_for(gate_statuses: dict[int, str]) -> float:
    """완료된 마지막 게이트 다음 위치 반환."""
    for gate_no in [5, 4, 3, 2, 1]:
        if gate_statuses.get(gate_no) == "done":
            _, _, _, gx = GATES[gate_no - 1]
            if gate_no == 5:
                return LAKEHOUSE_X
            return gx + 1.5
    # 아직 첫 게이트 전 — 벨트 시작
    return 5.0


def _sync_boxes(stage, entities: list[dict], gate_statuses: dict[int, str]) -> int:
    """namespace별 상자를 생성/이동/뱃지 추가/제거한다."""
    _ensure_scope(stage, "/World/LiveSync")
    active_ns = _extract_active_namespaces(entities)
    updated = 0

    # 완료된 namespace 상자 제거
    for ns in list(_box_state.keys()):
        if ns not in active_ns:
            _remove_box(stage, _box_state[ns]["box_path"])
            del _box_state[ns]
            updated += 1

    # 게이트별 완료 수
    done_gates = [no for no in range(1, 6) if gate_statuses.get(no) == "done"]
    target_x   = _box_x_for(gate_statuses)

    for ns in active_ns:
        safe     = ns.replace("-", "_").replace(".", "_")
        box_path = f"/World/LiveSync/Box_{safe}"

        if ns not in _box_state:
            # 신규 상자 생성
            _make_box(stage, box_path, target_x)
            _box_state[ns] = {"box_path": box_path, "badges": 0}
            carb.log_info(f"[trident.twin] Box created: {ns}")
            updated += 1

        state = _box_state[ns]

        # 이동
        if target_x != state.get("last_x"):
            _move_box(stage, box_path, target_x)
            state["last_x"] = target_x
            updated += 1

        # 완료 게이트 수만큼 뱃지 추가
        for gate_no in done_gates:
            if gate_no > state["badges"]:
                _, _, color, _ = GATES[gate_no - 1]
                _add_badge(stage, box_path, gate_no, color)
                state["badges"] = gate_no
                carb.log_info(f"[trident.twin] Badge {gate_no} added to {ns}")
                updated += 1

        # AUDIT 완료 → Lakehouse 이동 후 제거 예약
        if gate_statuses.get(5) == "done" and state.get("badges") >= 5:
            _move_box(stage, box_path, LAKEHOUSE_X + 3.0)
            _remove_box(stage, box_path)
            del _box_state[ns]
            updated += 1
            break

    return updated


# ── Extension ─────────────────────────────────────────────────────────────────

class TridentTwinExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        self._hub_url       = os.environ.get("TWIN_HUB_URL", DEFAULT_TWIN_HUB_URL)
        self._poll_interval = _env_float("TWIN_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)
        self._running       = False
        self._elapsed       = 0.0
        self._sub           = None

        self._window = ui.Window("Trident Twin Live", width=420, height=180)
        self._build_ui()

    def on_shutdown(self) -> None:
        self._stop()
        self._window = None

    def _build_ui(self) -> None:
        with self._window.frame:
            with ui.VStack(spacing=6):
                ui.Label("Trident Lakehouse Twin — Live Binding",
                         style={"font_size": 14})
                with ui.HStack(spacing=4):
                    ui.Label("twin-hub:", width=70)
                    self._url_field = ui.StringField()
                    self._url_field.model.set_value(self._hub_url)
                with ui.HStack(spacing=4):
                    ui.Label("Interval (s):", width=70)
                    self._int_field = ui.StringField()
                    self._int_field.model.set_value(str(int(self._poll_interval)))
                with ui.HStack(spacing=4):
                    ui.Button("Start Live", clicked_fn=self._start, width=100)
                    ui.Button("Stop",       clicked_fn=self._stop,  width=80)
                self._status = ui.Label("idle")
                self._detail = ui.Label("", style={"color": 0xFF8888AA})

    def _set_status(self, msg: str, detail: str = "") -> None:
        try:
            self._status.text = msg
            self._detail.text = detail
        except Exception:
            pass

    def _start(self) -> None:
        self._hub_url = self._url_field.model.get_value_as_string().strip() or DEFAULT_TWIN_HUB_URL
        try:
            self._poll_interval = max(2.0, float(self._int_field.model.get_value_as_string()))
        except ValueError:
            self._poll_interval = DEFAULT_POLL_INTERVAL

        if self._running:
            return
        self._running = True
        self._elapsed = self._poll_interval  # 첫 틱에 즉시 폴링
        app = omni.kit.app.get_app()
        self._sub = app.get_update_event_stream().create_subscription_to_pop(
            self._on_update, name="trident_twin_poll"
        )
        self._set_status(f"Live polling {self._hub_url} every {self._poll_interval:.0f}s")

    def _stop(self) -> None:
        self._running = False
        self._sub     = None
        self._set_status("Stopped.")

    def _on_update(self, event) -> None:
        if not self._running:
            return
        dt = event.payload.get("dt", 0.016)
        self._elapsed += dt
        if self._elapsed < self._poll_interval:
            return
        self._elapsed = 0.0

        entities = _fetch_entities(self._hub_url)
        if entities is None:
            self._set_status("Poll failed — twin-hub unreachable", f"url={self._hub_url}")
            return

        ctx   = omni.usd.get_context()
        stage = ctx.get_stage()
        if stage is None:
            self._set_status("No open stage.")
            return

        gate_statuses = _extract_gate_statuses(entities)
        updated       = _sync_boxes(stage, entities, gate_statuses)

        done_count = sum(1 for s in gate_statuses.values() if s == "done")
        self._set_status(
            f"Live — gates {done_count}/5 done  |  boxes {len(_box_state)}  |  {updated} updates",
            f"interval={self._poll_interval:.0f}s  hub={self._hub_url}",
        )
