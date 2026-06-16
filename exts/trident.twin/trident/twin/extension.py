"""Trident Twin Isaac Sim extension — live Lakehouse binding.

Polls twin-hub /api/twin/entities using Kit's update loop (no threading).

동작:
  - ingest 중인 namespace마다 컨베이어 벨트 위에 상자 prim 생성
  - 3개 축적 단계(STEP 1/2/3) 진행에 맞춰 상자 위치/뱃지를 갱신
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

CAMERA_TOPDOWN_PRESETS = {
    "/World/Cameras/Top_Overview": ((15.0, 7.0, 95.0), 14.0),
    "/World/Cameras/Top_Ingest": ((-22.0, 0.0, 22.0), 22.0),
    "/World/Cameras/Top_RawBucket": ((-4.0, -2.0, 32.0), 22.0),
    "/World/Cameras/zone_02_raw_bucket": ((-4.0, -2.0, 32.0), 22.0),
    "/World/Cameras/Top_Accumulation": ((12.6, 0.0, 18.0), 24.0),
    "/World/Cameras/Top_Lakehouse": ((29.0, -1.0, 30.0), 24.0),
    "/World/Cameras/zone_04_lakehouse": ((29.0, -1.0, 30.0), 24.0),
    "/World/Cameras/Top_Staging": ((29.0, 21.0, 34.0), 22.0),
    "/World/Cameras/zone_04_staging": ((29.0, 21.0, 34.0), 22.0),
    "/World/Cameras/Top_Search": ((44.0, 10.0, 18.0), 26.0),
    "/World/Cameras/Top_Delivery": ((59.0, 10.0, 22.0), 26.0),
    "/World/Cameras/Top_Tower": ((-22.0, 25.0, 22.0), 22.0),
}

CAMERA_LOOK_AT_PRESETS = {
    "/World/Cameras/Overview_Top45": ((25.0, -65.0, 65.0), (25.0, 10.0, 0.0), 12.0),
    "/World/Cameras/zone_01_truck_yard": ((-22.0, -22.0, 22.0), (-22.0, 0.0, 1.5), 18.0),
    "/World/Cameras/zone_03_accumulation": ((12.6, -12.0, 14.0), (12.6, 0.0, 1.2), 24.0),
    "/World/Cameras/zone_05_search": ((44.0, -2.0, 13.0), (44.0, 10.0, 1.2), 24.0),
    "/World/Cameras/zone_06_delivery": ((59.0, -5.0, 17.0), (59.0, 10.0, 1.2), 24.0),
    "/World/Cameras/zone_07_tower": ((-22.0, 10.0, 15.0), (-22.0, 25.0, 1.2), 24.0),
}

# 게이트 순서: (step_no, operation_id, 뱃지 색 RGB, 컨베이어 X 위치)
# The visual Accumulation Zone is intentionally three conceptual sections:
# STEP 1 ingest/profile, STEP 2 catalog/link, STEP 3 ready/manifest.
GATES = [
    (1, "ingest_profile",  Gf.Vec3f(0.80, 0.50, 0.10),  8.0666666667),
    (2, "catalog_link",    Gf.Vec3f(0.20, 0.80, 0.35), 12.6),
    (3, "ready_manifest",  Gf.Vec3f(0.15, 0.90, 0.45), 17.1333333333),
]

BELT_Y      =  -0.7    # main belt Y center
BELT_Z_TOP  =   0.70   # belt surface Z
BOX_SIDE    =   0.40   # 상자 한 변 길이
BOX_Z       =   BELT_Z_TOP + BOX_SIDE / 2
BADGE_SIDE  =   0.12
BADGE_Z_OFF =   BOX_SIDE / 2 + BADGE_SIDE / 2 + 0.02
LAKEHOUSE_X =   19.75   # READY 완료 후 Accumulation exit anchor

# namespace별 상자 상태
# { ns: { "box_path": str, "badges": int (완료 게이트 수) } }
_box_state: dict[str, dict[str, Any]] = {}
_completed_ingest_ns: set[str] = set()
_highlight_state: dict[str, dict[str, Any]] = {}
_delivery_state: list[dict[str, Any]] = []
_package_locations: dict[str, dict[str, Any]] = {}
_staging_state: dict[str, dict[str, Any]] = {}
_delivery_seq = 0


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


def _get_display_color(prim) -> Any:
    gprim = UsdGeom.Gprim(prim)
    if not gprim:
        return None
    attr = gprim.GetDisplayColorAttr()
    if attr and attr.HasAuthoredValueOpinion():
        return attr.Get()
    return None


def _restore_display_color(prim, value: Any) -> None:
    gprim = UsdGeom.Gprim(prim)
    if not gprim:
        return
    attr = gprim.GetDisplayColorAttr()
    if value is None:
        if attr:
            attr.Clear()
        return
    if not attr:
        attr = gprim.CreateDisplayColorAttr()
    attr.Set(value)


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


def _latest_command_seq(base_url: str) -> int:
    payload = _fetch_commands(base_url, 0)
    if not payload:
        return 0
    try:
        return int(payload.get("latest_seq", 0))
    except Exception:
        return 0


def _set_camera_focal(cam: UsdGeom.Camera, focal: float) -> None:
    attr = cam.GetFocalLengthAttr()
    if attr:
        attr.Set(float(focal))
    else:
        cam.CreateFocalLengthAttr(float(focal))


def _look_at_matrix(translate: tuple[float, float, float], look_at: tuple[float, float, float]) -> Gf.Matrix4d:
    eye = Gf.Vec3d(*translate)
    center = Gf.Vec3d(*look_at)
    up = Gf.Vec3d(0, 1, 0)
    fwd = (center - eye).GetNormalized()
    right = Gf.Cross(fwd, up).GetNormalized()
    up_corrected = Gf.Cross(right, fwd).GetNormalized()
    return Gf.Matrix4d(
        right[0],        right[1],        right[2],        0,
        up_corrected[0], up_corrected[1], up_corrected[2], 0,
        -fwd[0],         -fwd[1],         -fwd[2],         0,
        eye[0],          eye[1],          eye[2],          1,
    )


def _reset_authored_camera(stage, camera_path: str) -> None:
    if stage is None or not camera_path:
        return
    prim = stage.GetPrimAtPath(camera_path)
    if not prim or not prim.IsValid():
        return
    cam = UsdGeom.Camera(prim)
    xf = UsdGeom.Xformable(prim)
    if camera_path in CAMERA_LOOK_AT_PRESETS:
        translate, look_at, focal = CAMERA_LOOK_AT_PRESETS[camera_path]
        xf.ClearXformOpOrder()
        op = xf.AddXformOp(UsdGeom.XformOp.TypeTransform, UsdGeom.XformOp.PrecisionDouble)
        op.Set(_look_at_matrix(translate, look_at))
        _set_camera_focal(cam, focal)
    elif camera_path in CAMERA_TOPDOWN_PRESETS:
        translate, focal = CAMERA_TOPDOWN_PRESETS[camera_path]
        xf.ClearXformOpOrder()
        op = xf.AddTranslateOp(UsdGeom.XformOp.PrecisionDouble)
        op.Set(Gf.Vec3d(*translate))
        _set_camera_focal(cam, focal)


def _set_viewport_camera(camera_path: str, stage=None) -> None:
    if not camera_path:
        return
    _reset_authored_camera(stage, camera_path)
    try:
        from omni.kit.viewport.utility import get_active_viewport

        viewport = get_active_viewport()
        if viewport:
            # Re-clicking the same Portal camera should reset the viewport back
            # to the authored camera, not preserve a manually orbited view.
            if str(getattr(viewport, "camera_path", "") or "") == camera_path:
                try:
                    viewport.camera_path = "/OmniverseKit_Persp"
                except Exception:
                    pass
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


def _prim_translate(prim, fallback=(29.0, 2.0, 0.8)) -> tuple[float, float, float]:
    if prim is None or not prim.IsValid():
        return fallback
    try:
        xform = UsdGeom.Xformable(prim)
        for op in xform.GetOrderedXformOps():
            if op.GetOpType() == UsdGeom.XformOp.TypeTranslate:
                v = op.Get()
                return (float(v[0]), float(v[1]), float(v[2]))
    except Exception:
        pass
    return fallback


def _role_color(role: str) -> Gf.Vec3f:
    role = (role or "viewer").lower()
    if role in {"admin", "service"}:
        return Gf.Vec3f(0.95, 0.25, 0.20)
    if role == "operator":
        return Gf.Vec3f(0.95, 0.75, 0.10)
    if role == "researcher":
        return Gf.Vec3f(0.60, 0.35, 0.95)
    return Gf.Vec3f(0.20, 0.65, 0.95)


def _replace_active_viewer(stage, command: dict[str, Any]) -> None:
    if stage is None:
        return
    _ensure_scope(stage, "/World/Avatars")
    root_path = "/World/Avatars/ActiveUser"
    old = stage.GetPrimAtPath(root_path)
    if old.IsValid():
        stage.RemovePrim(old.GetPath())
    role = str(command.get("role") or "viewer")
    viewer_id = str(command.get("viewer_id") or command.get("user") or "portal-user")
    color = _role_color(role)
    root = UsdGeom.Xform.Define(stage, root_path)
    root.AddTranslateOp().Set(Gf.Vec3d(44.0, 8.0, 0.10))
    body = UsdGeom.Cube.Define(stage, f"{root_path}/Body")
    body.CreateSizeAttr(1.0)
    UsdGeom.XformCommonAPI(body).SetTranslate(Gf.Vec3d(0.0, 0.0, 0.75))
    UsdGeom.XformCommonAPI(body).SetScale(Gf.Vec3f(0.26, 0.18, 0.75))
    _set_display_color(body.GetPrim(), Gf.Vec3f(0.72, 0.78, 0.86))
    head = UsdGeom.Sphere.Define(stage, f"{root_path}/Head")
    head.CreateRadiusAttr(0.18)
    UsdGeom.XformCommonAPI(head).SetTranslate(Gf.Vec3d(0.0, 0.0, 1.62))
    _set_display_color(head.GetPrim(), Gf.Vec3f(0.92, 0.82, 0.70))
    badge = UsdGeom.Cube.Define(stage, f"{root_path}/RoleBadge")
    badge.CreateSizeAttr(1.0)
    UsdGeom.XformCommonAPI(badge).SetTranslate(Gf.Vec3d(0.0, 0.0, 1.98))
    UsdGeom.XformCommonAPI(badge).SetScale(Gf.Vec3f(0.32, 0.32, 0.10))
    _set_display_color(badge.GetPrim(), color)
    set_prim = root.GetPrim()
    set_prim.CreateAttribute("trident:entity_id", Sdf.ValueTypeNames.String).Set(f"viewer.{viewer_id}")
    set_prim.CreateAttribute("trident:entity_type", Sdf.ValueTypeNames.String).Set("active_viewer")
    set_prim.CreateAttribute("trident:role", Sdf.ValueTypeNames.String).Set(role)
    carb.log_info(f"[trident.twin] active viewer shown: {viewer_id} ({role})")


def _safe_token(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in value.replace("-", "_").replace(".", "_"))


def _scene_safe_name(value: str) -> str:
    return value.replace("-", "_").replace(".", "_").title()


def _namespace_from_entity_id(entity_id: str) -> str:
    parts = [p for p in entity_id.split(".") if p]
    if len(parts) >= 3 and parts[0] == "table":
        return parts[1]
    return ""


def _collect_gprims_under(prim) -> list[str]:
    result: list[str] = []
    if prim is None or not prim.IsValid():
        return result
    for item in Usd.PrimRange(prim):
        if item.IsA(UsdGeom.Gprim):
            result.append(str(item.GetPath()))
    return result


def _nearby_lakehouse_paths(stage, namespace: str, target_xyz: tuple[float, float, float]) -> list[str]:
    if not namespace:
        return []
    root = stage.GetPrimAtPath(f"/World/Lakehouse/Tables/{_scene_safe_name(namespace)}")
    if not root.IsValid():
        return []
    tx, ty, _ = target_xyz
    result: list[str] = []
    for item in Usd.PrimRange(root):
        path = str(item.GetPath())
        if not item.IsA(UsdGeom.Gprim):
            continue
        # Keep highlight tight: pulse the selected crate plus its small table
        # support/label, not the entire namespace slot/divider footprint.
        if any(token in path for token in ("/SlotBase", "/DividerS", "/DividerN", "/DividerW", "/DividerE")):
            continue
        # The selected table support and flat table-name label are separate from
        # the Iceberg table crate, so include nearby pieces in the same cell.
        if "/TableSupport_" in path or "/TableLabel_" in path:
            x, y, _z = _prim_translate(item)
            if abs(x - tx) <= 0.70 and abs(y - ty) <= 0.55:
                result.append(path)
    return result


def _create_highlight_plate(stage, entity_id: str, target_xyz: tuple[float, float, float]) -> str:
    root = "/World/LiveHighlights"
    _ensure_scope(stage, root)
    path = f"{root}/Selection_{_safe_token(entity_id)}"
    old = stage.GetPrimAtPath(path)
    if old.IsValid():
        stage.RemovePrim(old.GetPath())
    x, y, z = target_xyz
    plate = UsdGeom.Cube.Define(stage, path)
    plate.CreateSizeAttr(1.0)
    UsdGeom.XformCommonAPI(plate).SetTranslate(Gf.Vec3d(x, y, max(0.40, z - 0.12)))
    UsdGeom.XformCommonAPI(plate).SetScale(Gf.Vec3f(0.44, 0.36, 0.035))
    _set_display_color(plate.GetPrim(), Gf.Vec3f(1.0, 0.12, 0.12))
    return path


def _restore_highlight_state(stage, entity_id: str) -> None:
    state = _highlight_state.pop(entity_id, None)
    if not state or stage is None:
        return
    for entry in state.get("entries", []):
        prim = stage.GetPrimAtPath(entry.get("path", ""))
        if prim.IsValid() and prim.IsA(UsdGeom.Gprim):
            _restore_display_color(prim, entry.get("original"))
    for path in state.get("remove_paths", []):
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid():
            stage.RemovePrim(prim.GetPath())


def _clear_highlight_entity(stage, entity_id: str) -> None:
    if entity_id:
        _restore_highlight_state(stage, entity_id)


def _clear_workload(stage) -> None:
    if stage is None:
        return
    for entity_id in list(_highlight_state.keys()):
        _restore_highlight_state(stage, entity_id)
    for root_path in ("/World/LiveDelivery", "/World/LiveHighlights"):
        prim = stage.GetPrimAtPath(root_path)
        if prim.IsValid():
            stage.RemovePrim(prim.GetPath())
    _delivery_state.clear()
    staging_locations = {
        entity_id: state for entity_id, state in _package_locations.items()
        if str(state.get("path") or "").startswith("/World/LiveStaging/")
    }
    _package_locations.clear()
    _package_locations.update(staging_locations)
    carb.log_info("[trident.twin] workload visual state cleared")


def _highlight_entity(stage, entity_id: str, *, sticky: bool = True) -> bool:
    prim = _find_prim_by_entity_id(stage, entity_id)
    if prim is None:
        carb.log_warn(f"[trident.twin] highlight target not found: {entity_id}")
        return False

    # Re-highlighting while the item is blinking would otherwise save the
    # temporary blink color as the "original" role color. Restore first, then
    # rebuild the stronger whole-cell highlight.
    _restore_highlight_state(stage, entity_id)

    parent = prim.GetParent() if prim.GetParent().IsValid() else prim
    target_xyz = _prim_translate(prim)
    namespace = _namespace_from_entity_id(entity_id)

    paths: list[str] = []
    paths.extend(_collect_gprims_under(parent))  # crate + readiness badges
    paths.extend(_nearby_lakehouse_paths(stage, namespace, target_xyz))  # support/table label/dataset slot
    plate_path = _create_highlight_plate(stage, entity_id, target_xyz)
    paths.append(plate_path)

    # De-duplicate while preserving order and save original display colors so
    # blue data tables and yellow metadata tables return to their real role color.
    seen: set[str] = set()
    entries: list[dict[str, Any]] = []
    for path in paths:
        if path in seen:
            continue
        seen.add(path)
        p = stage.GetPrimAtPath(path)
        if p.IsValid() and p.IsA(UsdGeom.Gprim):
            entries.append({"path": path, "original": _get_display_color(p)})
            _set_display_color(p, Gf.Vec3f(1.0, 0.10, 0.10))

    _highlight_state[entity_id] = {
        "entries": entries,
        "remove_paths": [plate_path],
        "elapsed": 0.0,
        "duration": 10.0,
        "sticky": sticky,
    }
    carb.log_info(f"[trident.twin] highlighted dataset/table: {entity_id} paths={len(entries)}")
    return True


def _animate_highlights(stage, dt: float) -> None:
    if stage is None:
        return
    for entity_id in list(_highlight_state.keys()):
        state = _highlight_state[entity_id]
        state["elapsed"] = float(state.get("elapsed", 0.0)) + dt
        elapsed = state["elapsed"]
        color = Gf.Vec3f(1.0, 0.08, 0.08) if int(elapsed / 0.28) % 2 == 0 else Gf.Vec3f(1.0, 0.92, 0.05)
        for entry in state.get("entries", []):
            prim = stage.GetPrimAtPath(entry.get("path", ""))
            if prim.IsValid() and prim.IsA(UsdGeom.Gprim):
                _set_display_color(prim, color)
        if state.get("sticky"):
            continue
        if elapsed >= float(state.get("duration", 10.0)):
            _restore_highlight_state(stage, entity_id)


def _delivery_lane(workload_type: str) -> float:
    kind = (workload_type or "HPDA").upper()
    if kind == "AI":
        return 6.0
    if kind == "HPC":
        return 10.0
    return 14.0


def _interpolate(points: list[tuple[float, float, float]], t: float) -> tuple[float, float, float]:
    if not points:
        return (59.0, 10.0, 1.0)
    if len(points) == 1:
        return points[0]
    t = max(0.0, min(1.0, t))
    scaled = t * (len(points) - 1)
    idx = min(int(scaled), len(points) - 2)
    local = scaled - idx
    a = points[idx]
    b = points[idx + 1]
    return tuple(a[i] + (b[i] - a[i]) * local for i in range(3))  # type: ignore[return-value]


def _command_items(command: dict[str, Any]) -> list[dict[str, Any]]:
    raw_items = command.get("items")
    if isinstance(raw_items, list) and raw_items:
        return [item for item in raw_items if isinstance(item, dict) and str(item.get("entity_id") or "").strip()]
    entity_id = str(command.get("entity_id") or "").strip()
    if not entity_id:
        return []
    return [{
        "entity_id": entity_id,
        "label": command.get("label") or entity_id,
        "table": command.get("table"),
    }]


def _big_table_y(index: int, total: int) -> float:
    if total <= 1:
        return 10.0
    low, high = 6.7, 13.3
    return low + (high - low) * (index / max(1, total - 1))


_METADATA_TOKENS = ("manifest", "metadata", "catalog", "asset", "schema", "lineage", "link", "index")


def _table_component(entity_id: str, item: dict[str, Any] | None = None) -> str:
    table = str((item or {}).get("table") or "").strip()
    if table:
        return table.split(".")[-1]
    parts = [p for p in entity_id.split(".") if p]
    return parts[-1] if parts else entity_id


def _explicit_table_role(item: dict[str, Any] | None = None) -> str | None:
    if not isinstance(item, dict):
        return None
    for key in ("table_role", "role", "table_type"):
        value = str(item.get(key) or "").strip().lower()
        if value in {"data", "metadata"}:
            return value
    return None


def _table_role_for_package(stage, entity_id: str, item: dict[str, Any] | None = None) -> str:
    # Prefer the live catalog role carried by Portal/Twin Hub. Older scenes may
    # have mis-colored ``dataset_manifest`` from name-token inference; explicit
    # live role must win over stale prim attributes.
    explicit = _explicit_table_role(item)
    if explicit:
        return explicit
    prim = _find_prim_by_entity_id(stage, entity_id)
    if prim is not None and prim.IsValid():
        attr = prim.GetAttribute("trident:table_role")
        if attr and attr.Get():
            value = str(attr.Get()).lower()
            if value in {"data", "metadata"}:
                return value
    token = _table_component(entity_id, item).lower()
    return "metadata" if any(t in token for t in _METADATA_TOKENS) else "data"


def _table_role_color(role: str) -> Gf.Vec3f:
    if role == "metadata":
        return Gf.Vec3f(1.00, 0.78, 0.22)
    return Gf.Vec3f(0.38, 0.72, 1.00)


def _cube_child(stage, path: str, translate: tuple[float, float, float], scale: tuple[float, float, float], color: Gf.Vec3f):
    cube = UsdGeom.Cube.Define(stage, path)
    cube.CreateSizeAttr(1.0)
    UsdGeom.XformCommonAPI(cube).SetTranslate(Gf.Vec3d(*translate))
    UsdGeom.XformCommonAPI(cube).SetScale(Gf.Vec3f(*scale))
    _set_display_color(cube.GetPrim(), color)
    return cube.GetPrim()


def _make_table_crate_package(stage, root_path: str, *, entity_id: str, role: str) -> None:
    # Match the generated Lakehouse table crate proportions instead of using a
    # generic delivery cube: 0.26 x 0.20 x 0.16, role-colored body, tiny top
    # readiness badges on the front edge. Text labels are intentionally omitted
    # for moving packages because dynamic bitmap text is not available here.
    body = _cube_child(stage, f"{root_path}/TableCrate", (0.0, 0.0, 0.0), (0.26, 0.20, 0.16), _table_role_color(role))
    body.CreateAttribute("trident:source_entity_id", Sdf.ValueTypeNames.String).Set(entity_id)
    badge_colors = (
        Gf.Vec3f(0.20, 0.95, 0.30),
        Gf.Vec3f(0.20, 0.95, 0.30),
        Gf.Vec3f(0.20, 0.95, 0.30),
    )
    for idx, color in enumerate(badge_colors):
        _cube_child(
            stage,
            f"{root_path}/GateBadges/Ready_{idx + 1}",
            (-0.045 + idx * 0.045, -0.084, 0.088),
            (0.035, 0.026, 0.012),
            color,
        )



STAGING_TABLE_YS = (16.0, 20.0, 24.0)
STAGING_CENTER_X = 29.0
STAGING_CRATE_Z = 0.98
STAGING_ITEM_STEP_X = 0.64
STAGING_MAX_ITEMS_PER_BUNDLE = 9
STAGING_MAX_BUNDLES = 9

# Match the physical inbound rails generated by scripts/create_scene.py.
# Packages first exit the source zone on the east side, then ride the proper
# Lakehouse/Staging rail around Search Zone instead of cutting across it.
DELIVERY_RAIL_ENTRY_X = 37.7
DELIVERY_BIG_TABLE_X = 52.0
DELIVERY_LAKEHOUSE_RAIL_Y = 0.9
DELIVERY_STAGING_RAIL_Y = 19.6
DELIVERY_RAIL_Z = 1.05
DELIVERY_TABLE_Z = 1.18


def _staging_pos(bundle_index: int, item_index: int, total_items: int) -> tuple[float, float, float]:
    row = bundle_index % len(STAGING_TABLE_YS)
    lane = bundle_index // len(STAGING_TABLE_YS)
    count = max(1, min(total_items, STAGING_MAX_ITEMS_PER_BUNDLE))
    width = (count - 1) * STAGING_ITEM_STEP_X
    x = STAGING_CENTER_X - width / 2 + item_index * STAGING_ITEM_STEP_X + lane * 0.18
    y = STAGING_TABLE_YS[row]
    return (x, y, STAGING_CRATE_Z)


def _clear_live_staging(stage) -> None:
    root = stage.GetPrimAtPath("/World/LiveStaging")
    if root.IsValid():
        stage.RemovePrim(root.GetPath())
    for entity_id, state in list(_package_locations.items()):
        if str(state.get("path") or "").startswith("/World/LiveStaging/"):
            _package_locations.pop(entity_id, None)


def _rebuild_staging(stage) -> None:
    if stage is None:
        return
    _clear_live_staging(stage)
    if not _staging_state:
        return
    _ensure_scope(stage, "/World/LiveStaging")
    for bundle_index, (bundle_id, bundle) in enumerate(list(_staging_state.items())[:STAGING_MAX_BUNDLES]):
        items = [item for item in bundle.get("items", []) if isinstance(item, dict) and str(item.get("entity_id") or "").strip()]
        if not items:
            continue
        safe_bundle = _safe_token(bundle_id or f"bundle_{bundle_index}")[:64]
        bundle_root = f"/World/LiveStaging/Bundle_{bundle_index + 1:02d}_{safe_bundle}"
        _ensure_scope(stage, bundle_root)
        for item_index, item in enumerate(items[:STAGING_MAX_ITEMS_PER_BUNDLE]):
            entity_id = str(item.get("entity_id") or "").strip()
            if not entity_id:
                continue
            pos = _staging_pos(bundle_index, item_index, len(items))
            root_path = f"{bundle_root}/Item_{item_index + 1:02d}_{_safe_token(entity_id)[:48]}"
            xform = UsdGeom.Xform.Define(stage, root_path)
            xform.AddTranslateOp().Set(Gf.Vec3d(*pos))
            role = _table_role_for_package(stage, entity_id, item)
            _make_table_crate_package(stage, root_path, entity_id=entity_id, role=role)
            prim = xform.GetPrim()
            prim.CreateAttribute("trident:entity_id", Sdf.ValueTypeNames.String).Set(f"staging.{safe_bundle}.{entity_id}")
            prim.CreateAttribute("trident:entity_type", Sdf.ValueTypeNames.String).Set("staged_dataset_package")
            prim.CreateAttribute("trident:source_entity_id", Sdf.ValueTypeNames.String).Set(entity_id)
            prim.CreateAttribute("trident:bundle_id", Sdf.ValueTypeNames.String).Set(str(bundle_id))
            prim.CreateAttribute("trident:table_role", Sdf.ValueTypeNames.String).Set(role)
            # Keep staged package locations under a staging-specific key.
            # A selected Lakehouse table and its staged bundle can share the
            # same source entity_id; using entity_id as the only key made later
            # Data Search deliveries incorrectly start from the Staging Zone.
            _package_locations[f"staging:{safe_bundle}:{entity_id}"] = {
                "path": root_path,
                "pos": pos,
                "stage": "staging",
                "bundle_id": bundle_id,
                "source_entity_id": entity_id,
            }
    carb.log_info(f"[trident.twin] staging bundles rebuilt: {len(_staging_state)}")


def _apply_staging(stage, command: dict[str, Any]) -> None:
    if stage is None:
        return
    action = str(command.get("action") or "upsert").strip().lower()
    bundle_id = str(command.get("bundle_id") or command.get("selection_id") or "staged_bundle")
    if action == "clear":
        _staging_state.clear()
        _clear_live_staging(stage)
        carb.log_info("[trident.twin] staging cleared")
        return
    if action in {"sync", "replace"}:
        _staging_state.clear()
        raw_bundles = command.get("bundles")
        if isinstance(raw_bundles, list):
            for idx, bundle in enumerate(raw_bundles[:STAGING_MAX_BUNDLES]):
                if not isinstance(bundle, dict):
                    continue
                bid = str(bundle.get("id") or bundle.get("bundle_id") or f"bundle_{idx + 1}")
                items = [
                    item for item in (bundle.get("items") or [])
                    if isinstance(item, dict) and str(item.get("entity_id") or "").strip()
                ][:STAGING_MAX_ITEMS_PER_BUNDLE]
                if not items:
                    continue
                _staging_state[bid] = {
                    "title": bundle.get("title") or bid,
                    "items": items,
                    "query": bundle.get("query"),
                    "question": bundle.get("question"),
                }
        _rebuild_staging(stage)
        carb.log_info(f"[trident.twin] staging synced: {len(_staging_state)} bundles")
        return
    if action == "remove":
        _staging_state.pop(bundle_id, None)
        _rebuild_staging(stage)
        carb.log_info(f"[trident.twin] staging removed: {bundle_id}")
        return
    items = _command_items(command)
    if not items:
        return
    # Re-insert selected/upserted bundle at the front so the active basket is on
    # the nearest display table while preserving older Dataset Basket records.
    existing = {k: v for k, v in _staging_state.items() if k != bundle_id}
    _staging_state.clear()
    _staging_state[bundle_id] = {
        "title": command.get("title") or bundle_id,
        "items": items,
        "query": command.get("query"),
        "question": command.get("question"),
    }
    _staging_state.update(existing)
    _rebuild_staging(stage)
    carb.log_info(f"[trident.twin] staging {action}: {bundle_id} items={len(items)}")


def _find_staging_location(stage, entity_id: str) -> dict[str, Any] | None:
    """Return the staged package location for a source entity, if present."""
    for state in _package_locations.values():
        if state.get("stage") != "staging":
            continue
        if str(state.get("source_entity_id") or "") != entity_id:
            continue
        path = str(state.get("path") or "")
        prim = stage.GetPrimAtPath(path) if stage is not None else None
        if prim is not None and prim.IsValid():
            pos = _prim_translate(prim, state.get("pos") or (29.0, 20.0, STAGING_CRATE_Z))
            return {**state, "pos": pos}

    root = stage.GetPrimAtPath("/World/LiveStaging") if stage is not None else None
    if root is None or not root.IsValid():
        return None
    for prim in Usd.PrimRange(root):
        attr = prim.GetAttribute("trident:source_entity_id")
        if attr and attr.Get() == entity_id:
            return {
                "path": str(prim.GetPath()),
                "pos": _prim_translate(prim, (29.0, 20.0, STAGING_CRATE_Z)),
                "stage": "staging",
                "source_entity_id": entity_id,
            }
    return None


def _take_inflight_delivery(entity_id: str) -> dict[str, Any] | None:
    """Detach an in-flight package so a later command can reuse the same copy.

    Portal sends a Big Table command followed shortly by an AI Bus command. The
    Big Table animation lasts longer than that delay, so without this handoff a
    second moving package is created for a single selected table.
    """
    for state in list(_delivery_state):
        if str(state.get("entity_id") or "") != entity_id:
            continue
        duration = max(float(state.get("duration", 8.0)), 0.1)
        t = min(float(state.get("elapsed", 0.0)) / duration, 1.0)
        pos = _interpolate(state.get("points", []), t)
        _delivery_state.remove(state)
        return {
            "path": state.get("path"),
            "pos": pos,
            "stage": state.get("final_stage") or "delivery",
        }
    return None


def _make_or_reuse_package(stage, entity_id: str, start: tuple[float, float, float], *, destination: str, workload_type: str, item: dict[str, Any] | None = None) -> str:
    global _delivery_seq
    existing = _package_locations.get(entity_id)
    existing_path = str((existing or {}).get("path") or "")
    existing_is_staging = existing_path.startswith("/World/LiveStaging/")
    if destination == "ai_bus" and existing and not existing_is_staging:
        path = existing_path
        prim = stage.GetPrimAtPath(path)
        if prim.IsValid():
            return path
    if existing and not existing_is_staging:
        old = stage.GetPrimAtPath(existing_path)
        if old.IsValid():
            stage.RemovePrim(old.GetPath())
    _delivery_seq += 1
    root_path = f"/World/LiveDelivery/Package_{_delivery_seq:03d}_{_safe_token(entity_id)[:48]}"
    _ensure_scope(stage, "/World/LiveDelivery")
    xform = UsdGeom.Xform.Define(stage, root_path)
    xform.AddTranslateOp().Set(Gf.Vec3d(*start))
    role = _table_role_for_package(stage, entity_id, item)
    _make_table_crate_package(stage, root_path, entity_id=entity_id, role=role)
    xform.GetPrim().CreateAttribute("trident:entity_id", Sdf.ValueTypeNames.String).Set(f"delivery.{_delivery_seq:03d}.{entity_id}")
    xform.GetPrim().CreateAttribute("trident:entity_type", Sdf.ValueTypeNames.String).Set("live_delivery_package")
    xform.GetPrim().CreateAttribute("trident:source_entity_id", Sdf.ValueTypeNames.String).Set(entity_id)
    xform.GetPrim().CreateAttribute("trident:table_role", Sdf.ValueTypeNames.String).Set(role)
    return root_path


def _start_delivery_item(stage, item: dict[str, Any], *, destination: str, workload_type: str, origin: str, index: int, total: int) -> None:
    entity_id = str(item.get("entity_id") or "").strip()
    if not entity_id:
        return

    reuse = _take_inflight_delivery(entity_id) if destination == "ai_bus" else None
    root_path = str((reuse or {}).get("path") or "")

    if reuse and root_path and stage.GetPrimAtPath(root_path).IsValid():
        sx, sy, sz = reuse["pos"]
    else:
        prim = _find_prim_by_entity_id(stage, entity_id)
        sx, sy, sz = _prim_translate(prim, (29.0, 2.0, 0.9))

        if origin == "staging":
            staged = _find_staging_location(stage, entity_id)
            if staged and staged.get("pos"):
                sx, sy, sz = staged["pos"]
        elif origin != "lakehouse":
            # Backward-compatible fallback for old commands that had no origin.
            # Prefer non-staging package locations only; staging locations are
            # used exclusively when origin=staging is explicit.
            existing = _package_locations.get(entity_id)
            if existing and existing.get("pos") and existing.get("stage") != "staging":
                sx, sy, sz = existing["pos"]

    route_y = DELIVERY_STAGING_RAIL_Y if origin == "staging" else DELIVERY_LAKEHOUSE_RAIL_Y
    rail_entry_x = DELIVERY_RAIL_ENTRY_X
    detour_x = DELIVERY_BIG_TABLE_X
    big_y = _big_table_y(index, total)

    # Search/Lakehouse/Staging selections should not drag the original table
    # crate across the floor. The real table/staged crate stays in place and
    # only blinks; a matching copy appears directly on the correct inbound belt.
    # Offset multiple selected packages along the rail so 2/3-table bundles are
    # visible as separate boxes instead of overlapping.
    rail_spacing = 0.46
    rail_start_x = min(detour_x - 1.0, rail_entry_x + index * rail_spacing)
    rail_entry = (rail_start_x, route_y, DELIVERY_RAIL_Z)
    rail_to_table = (detour_x, route_y, DELIVERY_RAIL_Z)
    table_pos = (detour_x, big_y, DELIVERY_TABLE_Z)

    if reuse and root_path and stage.GetPrimAtPath(root_path).IsValid():
        start_z = max(float(sz), DELIVERY_RAIL_Z)
        start = (float(sx), float(sy), start_z)
    else:
        start = rail_entry
    if not root_path:
        root_path = _make_or_reuse_package(stage, entity_id, start, destination=destination, workload_type=workload_type, item=item)
    else:
        prim = stage.GetPrimAtPath(root_path)
        if prim.IsValid():
            _set_translate(prim, start[0], start[1], start[2])
    if destination in {"big_table", "selection_table", "table"}:
        points = [
            start,
            rail_to_table,
            table_pos,
        ]
        remove_on_finish = False
        final_stage = "big_table"
        duration = 8.0
    elif destination == "ai_bus":
        lane_y = _delivery_lane("AI")
        # Reused packages normally start on/near the Big Table. If a direct AI
        # command arrives without a prior Big Table leg, still route through the
        # proper inbound rail first.
        if float(sx) < DELIVERY_BIG_TABLE_X - 0.5:
            points = [start, rail_to_table, table_pos]
        else:
            points = [start, table_pos]
        points.extend([
            (54.0, big_y, DELIVERY_TABLE_Z),
            (54.0, lane_y, DELIVERY_TABLE_Z),
            (61.5, lane_y, DELIVERY_RAIL_Z),
        ])
        remove_on_finish = False
        final_stage = "ai_bus"
        duration = 6.0
    else:
        lane_y = _delivery_lane(workload_type)
        points = [
            start,
            rail_to_table,
            (detour_x, 10.0, DELIVERY_RAIL_Z),
            (61.5, lane_y, DELIVERY_RAIL_Z),
        ]
        remove_on_finish = True
        final_stage = "delivery"
        duration = 8.0

    _delivery_state.append({
        "path": root_path,
        "entity_id": entity_id,
        "points": points,
        "elapsed": 0.0,
        "duration": duration,
        "remove_on_finish": remove_on_finish,
        "final_stage": final_stage,
    })
    _highlight_entity(stage, entity_id)
    carb.log_info(f"[trident.twin] package move started: {entity_id} -> {destination}/{workload_type} origin={origin}")

def _start_delivery(stage, command: dict[str, Any]) -> None:
    if stage is None:
        return
    items = _command_items(command)
    if not items:
        return
    destination = str(command.get("destination") or "delivery").strip().lower()
    workload_type = str(command.get("workload_type") or "HPDA").strip().upper()
    origin = str(command.get("origin") or command.get("source") or command.get("delivery_origin") or "").strip().lower()
    if origin not in {"lakehouse", "staging"}:
        origin = ""
    for idx, item in enumerate(items):
        _start_delivery_item(stage, item, destination=destination, workload_type=workload_type, origin=origin, index=idx, total=len(items))


def _animate_deliveries(stage, dt: float) -> None:
    if stage is None:
        return
    for state in list(_delivery_state):
        state["elapsed"] = float(state.get("elapsed", 0.0)) + dt
        duration = max(float(state.get("duration", 8.0)), 0.1)
        t = min(state["elapsed"] / duration, 1.0)
        pos = _interpolate(state.get("points", []), t)
        prim = stage.GetPrimAtPath(state["path"])
        if prim.IsValid():
            _set_translate(prim, pos[0], pos[1], pos[2])
        if t >= 1.0:
            entity_id = str(state.get("entity_id") or "")
            if state.get("remove_on_finish"):
                if prim.IsValid():
                    stage.RemovePrim(prim.GetPath())
                _package_locations.pop(entity_id, None)
            else:
                _package_locations[entity_id] = {
                    "path": state.get("path"),
                    "pos": pos,
                    "stage": state.get("final_stage"),
                }
            _delivery_state.remove(state)


def _apply_command(stage, command: dict[str, Any]) -> None:
    kind = str(command.get("kind") or "")
    if kind == "camera":
        _set_viewport_camera(str(command.get("camera_path") or ""), stage)
    elif kind == "highlight":
        _highlight_entity(stage, str(command.get("entity_id") or ""), sticky=bool(command.get("sticky", True)))
    elif kind == "highlight_clear":
        _clear_highlight_entity(stage, str(command.get("entity_id") or ""))
    elif kind == "delivery":
        _start_delivery(stage, command)
    elif kind == "staging":
        _apply_staging(stage, command)
    elif kind == "workload_stop":
        _clear_workload(stage)
    elif kind == "viewer_state":
        _replace_active_viewer(stage, command)


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
    "struct_done":     2,
    "index_started":   3,
    "index_done":      3,
    "audit_started":   3,
    "audit_done":      3,
}

def _extract_active_namespaces(entities: list[dict]) -> dict[str, str]:
    """raw_bucket entity에서 현재 활성 namespace → latest ingest event 추출."""
    result: dict[str, str] = {}
    for e in entities:
        if e.get("type") != "raw_bucket":
            continue
        ns = e.get("namespace")
        if ns:
            result[ns] = str(e.get("event") or "")
    return result


def _active_ingest_progress(entities: list[dict]) -> tuple[int, int]:
    """Return (active namespace count, highest visible 3-step gate).

    The live scene has 3 conceptual Accumulation steps. Do not count the
    historical catalog pipeline_operation entities here; those can be 6/7+ and
    caused misleading status text such as "gates 6/3 done".
    """
    gates: list[int] = []
    for e in entities:
        if e.get("type") != "raw_bucket":
            continue
        event = str(e.get("event") or "")
        if event == "audit_done":
            continue
        gate = _EVENT_GATE.get(event, 0)
        if gate > 0:
            gates.append(gate)
    return len(gates), max(gates, default=0)


def _sync_boxes(stage, entities: list[dict]) -> int:
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

    for ns, event in active_ns.items():
        if event == "audit_done" and ns in _completed_ingest_ns:
            continue
        if event != "audit_done":
            _completed_ingest_ns.discard(ns)

        safe     = ns.replace("-", "_").replace(".", "_")
        box_path = f"/World/LiveSync/Box_{safe}"
        gate     = _EVENT_GATE.get(event, 0)
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

        # AUDIT 완료 → Lakehouse 방향으로 이동 후 제거.
        if event == "audit_done" and state.get("badges") >= len(GATES):
            _move_box(stage, box_path, LAKEHOUSE_X + 3.0)
            _remove_box(stage, box_path)
            del _box_state[ns]
            _completed_ingest_ns.add(ns)
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
        self._command_seq      = _latest_command_seq(self._hub_url)
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

        self._command_seq = max(self._command_seq, _latest_command_seq(self._hub_url))
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
        _completed_ingest_ns.clear()
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

        if stage is not None:
            _animate_highlights(stage, dt)
            _animate_deliveries(stage, dt)

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

        updated = _sync_boxes(stage, entities)
        active_count, current_step = _active_ingest_progress(entities)
        if active_count:
            status = f"Live — active ingest {active_count}  |  step {current_step}/{len(GATES)}  |  boxes {len(_box_state)}  |  {updated} updates"
        else:
            status = f"Live — idle  |  boxes {len(_box_state)}  |  {updated} updates"
        self._set_status(
            status,
            f"interval={self._poll_interval:.0f}s  hub={self._hub_url}",
        )
