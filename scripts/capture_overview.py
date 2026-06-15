"""Capture current Trident Twin scene screenshots from authored USD cameras.

The script opens the newest stages/trident_lakehouse_twin_*.usda file and
captures the same camera paths used by Portal/twin-hub. It must run inside the
Isaac Sim container because it needs isaacsim/omni/pxr.

Outputs under docs/screenshots/:
    overview_top90.png, overview_top45.png,
    zone_02_raw_bucket.png, zone_03_accumulation.png,
    zone_04_lakehouse.png, zone_04_staging.png,
    zone_05_search.png, zone_06_delivery.png, zone_07_tower.png

Run:
    /isaac-sim/python.sh scripts/capture_overview.py
"""
from __future__ import annotations

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
import omni.kit.app
import omni.renderer_capture
import omni.usd
from pxr import Gf, UsdGeom

BASE = Path(__file__).resolve().parents[1]
OUT_DIR = BASE / "docs" / "screenshots"

# Use authored scene cameras whenever present. Fallback definitions are only for
# older USD files that do not yet contain the current camera set.
CAMERA_OUTPUTS = [
    ("/World/Cameras/Overview_Top90", "overview_top90", (25.0, 10.0, 80.0), (25.0, 10.0, 0.0), 12.0),
    ("/World/Cameras/Overview_Top45", "overview_top45", (25.0, -65.0, 65.0), (25.0, 10.0, 0.0), 12.0),
    ("/World/Cameras/zone_02_raw_bucket", "zone_02_raw_bucket", (-4.0, -33.0, 42.0), (-4.0, 11.0, 1.4), 18.0),
    ("/World/Cameras/zone_03_accumulation", "zone_03_accumulation", (13.0, -18.0, 18.0), (13.0, 0.0, 1.4), 18.0),
    ("/World/Cameras/zone_04_lakehouse", "zone_04_lakehouse", (29.0, -31.0, 42.0), (29.0, 8.0, 1.4), 18.0),
    ("/World/Cameras/zone_04_staging", "zone_04_staging", (29.0, -4.0, 30.0), (29.0, 22.0, 1.2), 20.0),
    ("/World/Cameras/zone_05_search", "zone_05_search", (44.0, -2.0, 13.0), (44.0, 10.0, 1.2), 24.0),
    ("/World/Cameras/zone_06_delivery", "zone_06_delivery", (59.0, -5.0, 17.0), (59.0, 10.0, 1.2), 24.0),
    ("/World/Cameras/zone_07_tower", "zone_07_tower", (-22.0, 10.0, 15.0), (-22.0, 25.0, 1.2), 24.0),
]


def pump(n: int = 60) -> None:
    app = omni.kit.app.get_app()
    for _ in range(n):
        app.update()


def latest_stage() -> Path:
    pattern = str(BASE / "stages" / "trident_lakehouse_twin_*.usda")
    files = sorted(f for f in glob.glob(pattern) if "replay" not in Path(f).name)
    if not files:
        raise FileNotFoundError(f"scene file not found: {pattern}")
    return Path(files[-1])


def add_camera(stage, usd_path: str, translate, look_at, focal_mm: float) -> None:
    UsdGeom.Scope.Define(stage, "/World/Cameras")
    cam = UsdGeom.Camera.Define(stage, usd_path)
    eye = Gf.Vec3d(*translate)
    center = Gf.Vec3d(*look_at)
    up = Gf.Vec3d(0, 1, 0)
    fwd = (center - eye).GetNormalized()
    right = Gf.Cross(fwd, up).GetNormalized()
    up_corrected = Gf.Cross(right, fwd).GetNormalized()
    mat = Gf.Matrix4d(
        right[0], right[1], right[2], 0,
        up_corrected[0], up_corrected[1], up_corrected[2], 0,
        -fwd[0], -fwd[1], -fwd[2], 0,
        eye[0], eye[1], eye[2], 1,
    )
    xf = UsdGeom.Xformable(cam)
    xf.ClearXformOpOrder()
    op = xf.AddXformOp(UsdGeom.XformOp.TypeTransform, UsdGeom.XformOp.PrecisionDouble)
    op.Set(mat)
    cam.CreateFocalLengthAttr(float(focal_mm))
    cam.CreateClippingRangeAttr(Gf.Vec2f(0.1, 2000.0))


def capture_to_file(out_file: Path) -> None:
    rc = omni.renderer_capture.acquire_renderer_capture_interface()
    rc.capture_next_frame_swapchain_to_file(str(out_file))
    for _ in range(360):
        omni.kit.app.get_app().update()
        if out_file.exists() and out_file.stat().st_size > 0:
            return
    raise RuntimeError(f"capture did not produce {out_file}")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stage_path = latest_stage()
    print(f"open scene: {stage_path}")

    ctx = omni.usd.get_context()
    ctx.open_stage(str(stage_path))
    pump(180)
    stage = ctx.get_stage()

    try:
        from omni.kit.viewport.utility import get_active_viewport
        viewport = get_active_viewport()
        viewport.set_texture_resolution((2560, 1440))
    except Exception as exc:  # pragma: no cover - Isaac runtime only
        carb.log_warn(f"viewport utility unavailable: {exc}")
        viewport = None

    for cam_path, out_name, translate, look_at, focal in CAMERA_OUTPUTS:
        if not stage.GetPrimAtPath(cam_path).IsValid():
            add_camera(stage, cam_path, translate, look_at, focal)
            pump(30)
        if viewport is not None:
            viewport.camera_path = cam_path
        else:
            carb.settings.get_settings().set("/app/viewport/defaultCameraPath", cam_path)
        pump(150)
        out_file = OUT_DIR / f"{out_name}.png"
        capture_to_file(out_file)
        print(f"captured {out_file.name}: {out_file.stat().st_size:,} bytes")


if __name__ == "__main__":
    try:
        main()
    finally:
        simulation_app.close()
