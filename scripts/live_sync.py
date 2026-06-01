"""
live_sync.py
============
Isaac Sim 런타임에서 실행 — twin-hub /entities를 폴링해서
Accumulation Zone 게이트 badge와 컨베이어 상자를 실시간 업데이트한다.

실행:
  /isaac-sim/python.sh scripts/live_sync.py

환경변수:
  TWIN_HUB_URL   twin-hub base URL (기본: http://localhost:8765)
  POLL_INTERVAL  폴링 간격 초 (기본: 3)
  SCENE_PATH     열 usda 경로 (비워두면 stages/ 최신 파일 자동 선택)
"""
from __future__ import annotations

import os
import time
import json
import urllib.request
import urllib.error
from pathlib import Path

from isaacsim import SimulationApp

simulation_app = SimulationApp({"headless": False, "width": 1920, "height": 1080})

import omni.usd
import omni.kit.app
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

# ── 설정 ──────────────────────────────────────────────────────────────────────
TWIN_HUB_URL  = os.getenv("TWIN_HUB_URL", "http://localhost:8765").rstrip("/")
POLL_INTERVAL = float(os.getenv("POLL_INTERVAL", "3"))
STAGES_DIR    = Path(__file__).resolve().parents[1] / "stages"

# 게이트 번호 → (USD 경로 접두사, 컨베이어 X 위치)
GATE_INFO = {
    1: ("/World/DataReadiness/ProcessFlow/Step_01_INGEST", 7.0),
    2: ("/World/DataReadiness/ProcessFlow/Step_02_STRUCT", 10.0),
    3: ("/World/DataReadiness/ProcessFlow/Step_03_INDEX",  13.0),
    4: ("/World/DataReadiness/ProcessFlow/Step_04_EMBED",  16.0),
    5: ("/World/DataReadiness/ProcessFlow/Step_05_AUDIT",  19.0),
}

# 상태별 badge material 색상 (DisplayColor)
STATUS_COLOR = {
    "pending": Gf.Vec3f(0.35, 0.35, 0.35),   # 회색
    "running": Gf.Vec3f(0.95, 0.75, 0.05),   # 노랑
    "done":    Gf.Vec3f(0.10, 0.80, 0.20),   # 초록
}

# 컨베이어 벨트 Y, Z 기준
BELT_Y = -0.7
BELT_Z =  0.7 + 0.25   # belt top + box half-height
BOX_HALF = 0.25

# ── 씬 로드 ───────────────────────────────────────────────────────────────────

def _latest_usda() -> str:
    files = sorted(STAGES_DIR.glob("trident_lakehouse_twin_*.usda"), reverse=True)
    if not files:
        raise FileNotFoundError(f"No usda found in {STAGES_DIR}")
    return str(files[0])


def load_scene():
    scene_path = os.getenv("SCENE_PATH", "") or _latest_usda()
    print(f"[live_sync] Opening: {scene_path}")
    omni.usd.get_context().open_stage(scene_path)
    # 씬 로드 완료 대기
    for _ in range(60):
        simulation_app.update()
        if omni.usd.get_context().get_stage():
            break
        time.sleep(0.5)
    print("[live_sync] Scene loaded.")


# ── twin-hub 폴링 ─────────────────────────────────────────────────────────────

def fetch_entities() -> list[dict]:
    try:
        req = urllib.request.Request(f"{TWIN_HUB_URL}/entities")
        with urllib.request.urlopen(req, timeout=4) as r:
            data = json.loads(r.read())
            return data.get("entities", [])
    except Exception as e:
        print(f"[live_sync] fetch error: {e}")
        return []


def extract_gate_statuses(entities: list[dict]) -> dict[int, str]:
    """entity 목록에서 게이트별 status 추출."""
    result = {}
    for e in entities:
        if e.get("type") != "pipeline_operation":
            continue
        no = e.get("step_no")
        if no:
            result[int(no)] = e.get("status", "pending")
    return result


# ── prim 조작 ─────────────────────────────────────────────────────────────────

def _set_display_color(prim, color: Gf.Vec3f):
    """GPrim displayColor를 직접 설정 (material 교체 없이 색상만 변경)."""
    gprim = UsdGeom.Gprim(prim)
    if not gprim:
        return
    attr = gprim.GetDisplayColorAttr()
    if not attr:
        attr = gprim.CreateDisplayColorAttr()
    attr.Set([color])


def update_gate_badge(stage: Usd.Stage, gate_no: int, status: str):
    """게이트 badge prim 색상을 status에 맞게 업데이트."""
    path_prefix, _ = GATE_INFO[gate_no]
    badge_path = f"{path_prefix}/Badge"
    prim = stage.GetPrimAtPath(badge_path)
    if not prim.IsValid():
        return
    color = STATUS_COLOR.get(status, STATUS_COLOR["pending"])
    _set_display_color(prim, color)


# ── 컨베이어 상자 관리 ────────────────────────────────────────────────────────

_active_boxes: dict[str, str] = {}   # ns → box prim path


def _box_path(ns: str) -> str:
    safe = ns.replace("-", "_").replace(".", "_")
    return f"/World/LiveSync/Box_{safe}"


def ensure_live_scope(stage: Usd.Stage):
    scope = stage.GetPrimAtPath("/World/LiveSync")
    if not scope.IsValid():
        UsdGeom.Scope.Define(stage, "/World/LiveSync")


def _make_box(stage: Usd.Stage, path: str, x: float):
    """컨베이어 위에 상자 prim 생성."""
    xform = UsdGeom.Xform.Define(stage, path)
    cube = UsdGeom.Cube.Define(stage, f"{path}/Body")
    cube.GetSizeAttr().Set(1.0)
    xform_op = xform.AddTranslateOp()
    xform_op.Set(Gf.Vec3d(x, BELT_Y, BELT_Z))
    scale_op = xform.AddScaleOp()
    scale_op.Set(Gf.Vec3f(BOX_HALF * 2, BOX_HALF * 2, BOX_HALF * 2))
    _set_display_color(cube.GetPrim(), Gf.Vec3f(0.80, 0.55, 0.20))  # 브론즈
    return xform.GetPrim()


def _move_box(stage: Usd.Stage, path: str, x: float):
    """상자 X 위치 이동."""
    prim = stage.GetPrimAtPath(path)
    if not prim.IsValid():
        return
    xform = UsdGeom.Xform(prim)
    ops = xform.GetOrderedXformOps()
    for op in ops:
        if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
            cur = op.Get()
            op.Set(Gf.Vec3d(x, cur[1], cur[2]))
            break


def _remove_box(stage: Usd.Stage, path: str):
    """상자 prim 제거."""
    prim = stage.GetPrimAtPath(path)
    if prim.IsValid():
        stage.RemovePrim(prim.GetPath())


def update_conveyor_boxes(stage: Usd.Stage, entities: list[dict], gate_statuses: dict[int, str]):
    """raw_bucket entity 기반으로 컨베이어 상자를 생성/이동/제거."""
    ensure_live_scope(stage)

    # 현재 ingest 중인 namespace 목록
    active_ns = {
        e["namespace"]: e
        for e in entities
        if e.get("type") == "raw_bucket" and e.get("status") in ("running", "pending")
    }
    done_ns = {
        e["namespace"]
        for e in entities
        if e.get("type") == "raw_bucket" and e.get("status") == "PASS"
    }

    # 완료된 namespace 상자 제거
    for ns in list(_active_boxes.keys()):
        if ns in done_ns:
            _remove_box(stage, _active_boxes.pop(ns))

    # 게이트 상태로 상자 X 위치 결정
    # 마지막 done 게이트 다음 위치로 이동
    def _box_x_for_ns(audit_status: str) -> float:
        # 각 게이트 done 수로 위치 결정
        for gate_no in [5, 4, 3, 2, 1]:
            if gate_statuses.get(gate_no) == "done":
                _, gx = GATE_INFO[gate_no]
                return gx + 1.5  # 게이트 통과 후
        return 5.5  # 아직 첫 게이트 전

    for ns, entity in active_ns.items():
        box_path = _box_path(ns)
        target_x = _box_x_for_ns(entity.get("status", "pending"))
        if ns not in _active_boxes:
            _make_box(stage, box_path, target_x)
            _active_boxes[ns] = box_path
            print(f"[live_sync] Box created: {ns} @ x={target_x:.1f}")
        else:
            _move_box(stage, box_path, target_x)


# ── 메인 루프 ─────────────────────────────────────────────────────────────────

def main():
    load_scene()

    prev_statuses: dict[int, str] = {}

    print(f"[live_sync] Polling {TWIN_HUB_URL} every {POLL_INTERVAL}s ...")

    while simulation_app.is_running():
        simulation_app.update()

        entities = fetch_entities()
        if not entities:
            time.sleep(POLL_INTERVAL)
            continue

        gate_statuses = extract_gate_statuses(entities)
        stage = omni.usd.get_context().get_stage()
        if not stage:
            time.sleep(POLL_INTERVAL)
            continue

        # 게이트 badge 색상 업데이트 (변화 있을 때만)
        for gate_no in range(1, 6):
            new_status = gate_statuses.get(gate_no, "pending")
            if prev_statuses.get(gate_no) != new_status:
                update_gate_badge(stage, gate_no, new_status)
                print(f"[live_sync] Gate {gate_no} → {new_status}")

        prev_statuses = dict(gate_statuses)

        # 컨베이어 상자 업데이트
        update_conveyor_boxes(stage, entities, gate_statuses)

        time.sleep(POLL_INTERVAL)

    print("[live_sync] Shutting down.")


if __name__ == "__main__":
    main()
    simulation_app.close()
