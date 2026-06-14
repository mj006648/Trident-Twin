"""Trident Twin Isaac Sim extension — live Lakehouse binding.

Polls twin-hub /api/twin/entities using Kit's update loop (no threading).

동작:
  - ingest 중인 namespace마다 컨베이어 벨트 위에 상자 prim 생성
  - 각 게이트(INGEST/STRUCT/INDEX/EMBED/AUDIT) 완료 시 해당 뱃지를 상자에 attach
  - 상자는 완료된 마지막 게이트 다음 위치로 이동
  - AUDIT 완료 시 Lakehouse 방향으로 이동 후 제거

Environment variables:
  TWIN_HUB_URL                  twin-hub base URL (default: http://10.38.38.223:8765)
  TWIN_POLL_INTERVAL            live entity poll cadence in seconds (default: 5)
  TWIN_COMMAND_POLL_INTERVAL    camera/highlight command poll cadence in seconds (default: 1)
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import carb
import omni.ext
import omni.kit.app
import omni.ui as ui
import omni.usd
from pxr import Gf, Sdf, Usd, UsdGeom

DEFAULT_TWIN_HUB_URL  = "http://10.38.38.223:8765"
DEFAULT_POLL_INTERVAL = 5.0
DEFAULT_COMMAND_INTERVAL = 1.0
DEFAULT_SCENE_CAMERA = "/World/Cameras/Overview_Top45"

# 게이트 순서: (step_no, operation_id, 뱃지 색 RGB, 컨베이어 X 위치)
GATES = [
    (1, "object_schema_profile",  Gf.Vec3f(0.80, 0.50, 0.10),  6.5),
    (2, "cardinality_materialize",Gf.Vec3f(0.40, 0.65, 0.95),  8.8),
    (3, "catalog_tables_columns", Gf.Vec3f(0.20, 0.80, 0.35), 11.1),
    (4, "asset_link_audit",      Gf.Vec3f(0.95, 0.75, 0.05), 13.4),
    (5, "redis_component_graph", Gf.Vec3f(0.35, 0.85, 0.85), 15.7),
    (6, "milvus_semantic_index", Gf.Vec3f(0.75, 0.30, 0.90), 18.0),
    (7, "dataset_ready_status",  Gf.Vec3f(0.15, 0.90, 0.45), 20.3),
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


def _env_bool(key: str, default: bool = True) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _latest_scene_path() -> Path | None:
    explicit = os.environ.get("SCENE_PATH", "").strip()
    if explicit:
        return Path(explicit)
    stages_dir = _repo_root() / "stages"
    files = sorted(
        p for p in stages_dir.glob("trident_lakehouse_twin_*.usda")
        if "replay" not in p.name and p.stat().st_size > 1024
    )
    return files[-1] if files else None


def _open_latest_scene_if_requested() -> bool:
    scene_path = _latest_scene_path()
    if scene_path is None:
        carb.log_warn("[trident.twin] no generated scene found to auto-open")
        return False
    ctx = omni.usd.get_context()
    carb.log_info(f"[trident.twin] opening scene: {scene_path}")
    ctx.open_stage(str(scene_path))
    _set_viewport_camera(os.environ.get("TRIDENT_TWIN_DEFAULT_CAMERA", DEFAULT_SCENE_CAMERA))
    carb.log_info(f"[trident.twin] scene open requested: {scene_path.name}")
    return True


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
    """컨베이어 위에 상자 prim 생성. 이미 존재하면 위치만 업데이트한다."""
    existing = stage.GetPrimAtPath(path)
    if existing.IsValid():
        _set_translate(existing, x, BELT_Y, BOX_Z)
        return
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


def _add_badge(stage, box_path: str, badge_no: int, color: Gf.Vec3f, box_x: float = 0.0) -> None:
    """상자 위에 뱃지 cube를 월드 좌표 독립 prim으로 배치."""
    badge_path = f"{box_path}/Badge_{badge_no:02d}"
    if stage.GetPrimAtPath(badge_path).IsValid():
        return
    badge_x_off = (badge_no - 3) * (BADGE_SIDE + 0.02)
    world_x = box_x + badge_x_off
    world_z = BOX_Z + BOX_SIDE / 2 + BADGE_SIDE / 2 + 0.02
    xform = UsdGeom.Xform.Define(stage, badge_path)
    xform.AddTranslateOp().Set(Gf.Vec3d(world_x, BELT_Y, world_z))
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


def _fetch_commands(base_url: str, since: int) -> dict[str, Any] | None:
    try:
        req = urllib.request.Request(base_url.rstrip("/") + f"/api/twin/commands?since={since}")
        with urllib.request.urlopen(req, timeout=2.0) as r:
            return json.loads(r.read().decode("utf-8"))
    except Exception as e:
        carb.log_warn(f"[trident.twin] command fetch failed: {e}")
        return None


def _set_viewport_camera(camera_path: str) -> None:
    if not camera_path:
        return
    try:
        from omni.kit.viewport.utility import get_active_viewport

        viewport = get_active_viewport()
        if viewport:
            viewport.camera_path = camera_path
            carb.log_info(f"[trident.twin] camera switched: {camera_path}")
            return
    except Exception as e:  # pragma: no cover - Isaac runtime only
        carb.log_warn(f"[trident.twin] viewport camera switch failed: {e}")
    try:
        carb.settings.get_settings().set("/app/viewport/defaultCameraPath", camera_path)
    except Exception as e:  # pragma: no cover - Isaac runtime only
        carb.log_warn(f"[trident.twin] default camera setting failed: {e}")


def _find_prim_by_entity_id(stage, entity_id: str):
    if not stage or not entity_id:
        return None
    for prim in stage.Traverse():
        attr = prim.GetAttribute("trident:entity_id")
        if attr and attr.Get() == entity_id:
            return prim
    return None


def _highlight_entity(stage, entity_id: str) -> bool:
    prim = _find_prim_by_entity_id(stage, entity_id)
    if prim is None:
        carb.log_warn(f"[trident.twin] highlight target not found: {entity_id}")
        return False
    for item in Usd.PrimRange(prim):
        if item.IsA(UsdGeom.Gprim):
            _set_display_color(item, Gf.Vec3f(0.05, 0.75, 0.90))
    carb.log_info(f"[trident.twin] highlighted: {entity_id}")
    return True


def _apply_command(stage, command: dict[str, Any]) -> None:
    kind = str(command.get("kind") or "")
    if kind == "camera":
        _set_viewport_camera(str(command.get("camera_path") or ""))
    elif kind == "highlight":
        _highlight_entity(stage, str(command.get("entity_id") or ""))


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


# ingest 이벤트 → 게이트 번호 매핑
_EVENT_GATE: dict[str, int] = {
    "analyze_started": 1,
    "struct_started":  2,
    "struct_done":     4,
    "index_started":   5,
    "index_done":      6,
    "audit_started":   7,
    "audit_done":      7,
}

def _extract_active_namespaces(entities: list[dict]) -> dict[str, str]:
    """raw_bucket entity에서 현재 활성 namespace → status 추출."""
    result: dict[str, str] = {}
    for e in entities:
        if e.get("type") != "raw_bucket":
            continue
        ns = e.get("namespace")
        if ns:
            result[ns] = e.get("status", "pending")
    return result

def _gate_from_entities(entities: list[dict], ns: str) -> int:
    """namespace 의 raw_bucket event 에서 현재 완료 게이트 번호를 반환한다."""
    for e in entities:
        if e.get("type") == "raw_bucket" and e.get("namespace") == ns:
            evt = e.get("event", "")
            return _EVENT_GATE.get(evt, 0)
    return 0


def _box_x_for(gate_statuses: dict[int, str]) -> float:
    """완료된 마지막 게이트 다음 위치 반환."""
    for gate_no in range(len(GATES), 0, -1):
        if gate_statuses.get(gate_no) == "done":
            _, _, _, gx = GATES[gate_no - 1]
            if gate_no == len(GATES):
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

    for ns in active_ns:
        safe     = ns.replace("-", "_").replace(".", "_")
        box_path = f"/World/LiveSync/Box_{safe}"
        gate     = _gate_from_entities(entities, ns)
        # gate: 0=이벤트없음(skip), 1..N=current catalog-first pipeline gate
        if gate == 0:
            continue  # 아직 이벤트 없음 — 박스 생성 안 함
        elif gate <= len(GATES):
            target_x = GATES[min(gate - 1, len(GATES) - 1)][3]
        else:
            target_x = LAKEHOUSE_X
        done_gates = list(range(1, min(gate + 1, len(GATES) + 1)))

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
        cur_x = state.get("last_x", target_x)
        for gate_no in done_gates:
            if gate_no > state["badges"]:
                _, _, color, _ = GATES[gate_no - 1]
                _add_badge(stage, box_path, gate_no, color, box_x=cur_x)
                state["badges"] = gate_no
                carb.log_info(f"[trident.twin] Badge {gate_no} added to {ns}")
                updated += 1

        # AUDIT 완료 → Lakehouse 이동 후 제거 예약
        if gate_statuses.get(len(GATES)) == "done" and state.get("badges") >= len(GATES):
            _move_box(stage, box_path, LAKEHOUSE_X + 3.0)
            _remove_box(stage, box_path)
            del _box_state[ns]
            updated += 1
            break

    return updated


# ── Extension ─────────────────────────────────────────────────────────────────

class TridentTwinExtension(omni.ext.IExt):

    def on_startup(self, ext_id: str) -> None:
        self._hub_url          = os.environ.get("TWIN_HUB_URL", DEFAULT_TWIN_HUB_URL)
        self._poll_interval    = _env_float("TWIN_POLL_INTERVAL", DEFAULT_POLL_INTERVAL)
        self._command_interval = _env_float("TWIN_COMMAND_POLL_INTERVAL", DEFAULT_COMMAND_INTERVAL)
        self._running          = False
        self._elapsed          = 0.0
        self._command_elapsed  = self._command_interval
        self._command_seq      = 0
        self._sub              = None
        self._auto_open_pending = _env_bool("TWIN_AUTO_OPEN_SCENE", False)
        self._auto_start_live   = _env_bool("TWIN_AUTO_START_LIVE", True)

        self._window = ui.Window("Trident Twin Live", width=420, height=180)
        self._build_ui()
        app = omni.kit.app.get_app()
        self._sub = app.get_update_event_stream().create_subscription_to_pop(
            self._on_update, name="trident_twin_update"
        )
        if self._auto_start_live:
            self._start()

    def on_shutdown(self) -> None:
        self._stop()
        self._sub = None
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
        if self._sub is None:
            app = omni.kit.app.get_app()
            self._sub = app.get_update_event_stream().create_subscription_to_pop(
                self._on_update, name="trident_twin_update"
            )
        self._set_status(f"Live polling {self._hub_url} every {self._poll_interval:.0f}s")

    def _stop(self) -> None:
        self._running = False
        _box_state.clear()
        # twin-hub ingest 이벤트 초기화
        try:
            import urllib.request as _ur
            req = _ur.Request(f"{self._hub_url}/api/twin/ingest/clear", method="DELETE")
            _ur.urlopen(req, timeout=2)
        except Exception:
            pass
        # /World/LiveSync scope 삭제 — 씬 초기화
        try:
            ctx = omni.usd.get_context()
            stage = ctx.get_stage()
            if stage:
                prim = stage.GetPrimAtPath("/World/LiveSync")
                if prim.IsValid():
                    stage.RemovePrim(prim.GetPath())
        except Exception:
            pass
        self._set_status("Stopped.")

    def _on_update(self, event) -> None:
        payload = getattr(event, "payload", {}) or {}
        dt = float(payload.get("dt", 0.016))

        if self._auto_open_pending:
            self._auto_open_pending = False
            _open_latest_scene_if_requested()

        ctx = omni.usd.get_context()
        stage = ctx.get_stage()

        self._command_elapsed += dt
        if self._command_elapsed >= self._command_interval:
            self._command_elapsed = 0.0
            commands_payload = _fetch_commands(self._hub_url, self._command_seq)
            if commands_payload is not None:
                for command in commands_payload.get("commands", []):
                    _apply_command(stage, command)
                self._command_seq = int(commands_payload.get("latest_seq", self._command_seq))

        if not self._running:
            return

        self._elapsed += dt
        if self._elapsed < self._poll_interval:
            return
        self._elapsed = 0.0

        entities = _fetch_entities(self._hub_url)
        if entities is None:
            self._set_status("Poll failed — twin-hub unreachable", f"url={self._hub_url}")
            return

        if stage is None:
            self._set_status("No open stage.")
            return

        gate_statuses = _extract_gate_statuses(entities)
        updated       = _sync_boxes(stage, entities, gate_statuses)

        done_count = sum(1 for s in gate_statuses.values() if s == "done")
        self._set_status(
            f"Live — gates {done_count}/{len(GATES)} done  |  boxes {len(_box_state)}  |  {updated} updates",
            f"interval={self._poll_interval:.0f}s  hub={self._hub_url}",
        )
