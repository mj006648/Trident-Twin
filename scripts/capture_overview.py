"""Trident Twin 씬 개요 스크린샷 캡처.

최신 stages/trident_lakehouse_twin_*.usda 파일을 열고
전체 씬 2장 + 존별 45도 7장을 저장한다.

출력: docs/screenshots/overview_top90.png
      docs/screenshots/overview_top45.png
      docs/screenshots/zone_01_truck_yard.png
      docs/screenshots/zone_02_raw_bucket.png
      docs/screenshots/zone_03_accumulation.png
      docs/screenshots/zone_04_lakehouse.png
      docs/screenshots/zone_05_search.png
      docs/screenshots/zone_06_delivery.png
      docs/screenshots/zone_07_tower.png

실행:
    /isaac-sim/python.sh scripts/capture_overview.py
"""
from isaacsim import SimulationApp

simulation_app = SimulationApp({
    "headless": True,
    "width": 2560,
    "height": 1440,
    "anti_aliasing": 3,
})

import glob
from pathlib import Path

import carb
import omni.usd
import omni.kit.app
import omni.renderer_capture
from pxr import Gf, UsdGeom

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "docs" / "screenshots"

# 씬 전체 중심 (X=20, Y=10)
SCENE_CX, SCENE_CY = 20.0, 10.0

def _zone_cam(name, cx, cy, dist, usd_name):
    """존 중심(cx,cy)에서 남서쪽 45도 카메라 튜플 생성."""
    return (
        f"/World/Cameras/{usd_name}",
        (cx - dist * 0.6, cy - dist, dist),
        (cx, cy, 1.5),
        18.0,
        usd_name,
    )

CAMERAS = [
    # 전체 씬 2장
    (
        "/World/Cameras/Overview_Top90",
        (SCENE_CX + 5.0, SCENE_CY, 80.0),
        (SCENE_CX + 5.0, SCENE_CY, 0.0),
        12.0,
        "overview_top90",
    ),
    (
        "/World/Cameras/Overview_Top45",
        (SCENE_CX + 5.0, SCENE_CY - 75.0, 65.0),
        (SCENE_CX + 5.0, SCENE_CY, 0.0),
        12.0,
        "overview_top45",
    ),
    # 존별 45도 (cx, cy, dist)
    _zone_cam("Truck Yard",    -22,  0,  22, "zone_01_truck_yard"),
    _zone_cam("Raw Bucket",     -4, 11,  28, "zone_02_raw_bucket"),
    _zone_cam("Accumulation",  +13,  0,  18, "zone_03_accumulation"),
    _zone_cam("Lakehouse",     +29, 11,  28, "zone_04_lakehouse"),
    _zone_cam("Search",        +44, 10,  16, "zone_05_search"),
    _zone_cam("Delivery",      +59, 10,  22, "zone_06_delivery"),
    _zone_cam("Tower",         -22, 25,  18, "zone_07_tower"),
]


def pump(n: int = 60) -> None:
    app = omni.kit.app.get_app()
    for _ in range(n):
        app.update()


def latest_stage() -> Path:
    pattern = str(BASE / "stages" / "trident_lakehouse_twin_*.usda")
    files = sorted(
        f for f in glob.glob(pattern)
        if "replay" not in Path(f).name
    )
    if not files:
        raise FileNotFoundError(f"씬 파일 없음: {pattern}")
    return Path(files[-1])


def add_camera(stage, usd_path, translate, look_at, focal_mm):
    """look_at: (x,y,z) 월드 좌표. 카메라가 그 지점을 바라보도록 행렬 설정."""
    from pxr import Gf as _Gf
    UsdGeom.Scope.Define(stage, "/World/Cameras")
    cam = UsdGeom.Camera.Define(stage, usd_path)
    eye = _Gf.Vec3d(*translate)
    center = _Gf.Vec3d(*look_at)
    up = _Gf.Vec3d(0, 1, 0)
    fwd = (center - eye).GetNormalized()
    right = _Gf.Cross(fwd, up).GetNormalized()
    up_corrected = _Gf.Cross(right, fwd).GetNormalized()
    # 행 우선 GfMatrix4d (USD는 row-major)
    m = _Gf.Matrix4d(
        right[0],        right[1],        right[2],        0,
        up_corrected[0], up_corrected[1], up_corrected[2], 0,
        -fwd[0],         -fwd[1],         -fwd[2],         0,
        eye[0],          eye[1],          eye[2],          1,
    )
    xf = UsdGeom.Xformable(cam)
    xf.ClearXformOpOrder()
    op = xf.AddXformOp(UsdGeom.XformOp.TypeTransform, UsdGeom.XformOp.PrecisionDouble)
    op.Set(m)
    cam.CreateFocalLengthAttr(focal_mm)
    cam.CreateClippingRangeAttr(_Gf.Vec2f(0.1, 2000.0))


def capture_to_file(cam_path: str, out_file: Path) -> None:
    rc = omni.renderer_capture.acquire_renderer_capture_interface()
    rc.capture_next_frame_swapchain_to_file(str(out_file))
    # pump until file appears (async write)
    for _ in range(300):
        omni.kit.app.get_app().update()
        if out_file.exists() and out_file.stat().st_size > 0:
            break


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    stage_path = latest_stage()
    print(f"씬 로드: {stage_path.name}")

    ctx = omni.usd.get_context()
    ctx.open_stage(str(stage_path))
    pump(150)

    stage = ctx.get_stage()

    # viewport 카메라 설정
    try:
        from omni.kit.viewport.utility import get_active_viewport
        viewport = get_active_viewport()
        viewport.set_texture_resolution((2560, 1440))
    except Exception as e:
        carb.log_warn(f"viewport utility 없음: {e}")
        viewport = None

    for usd_path, translate, rotate, focal, out_name in CAMERAS:
        add_camera(stage, usd_path, translate, rotate, focal)
        pump(30)

        if viewport is not None:
            viewport.camera_path = usd_path
        else:
            carb.settings.get_settings().set("/app/viewport/defaultCameraPath", usd_path)

        pump(120)

        out_file = OUT_DIR / f"{out_name}.png"
        capture_to_file(usd_path, out_file)
        size = out_file.stat().st_size if out_file.exists() else 0
        print(f"  -> {out_file.name}  ({size:,} bytes)")


if __name__ == "__main__":
    main()
    simulation_app.close()
