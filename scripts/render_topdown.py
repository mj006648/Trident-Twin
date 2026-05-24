"""Render the 9 top-down cameras of the Trident-Twin scene as PNGs.

Loads stages/trident_lakehouse_twin_replay.usda headless, sets each of the
/World/Cameras/Top_* cameras as the active viewport camera in turn, and
writes a frame to docs/screenshots/<CameraName>.png.

Run:
    /home/chang/isaac-sim/python.sh scripts/render_topdown.py
"""
from isaacsim import SimulationApp

simulation_app = SimulationApp({
    "headless": True,
    "width": 1920,
    "height": 1080,
})

from pathlib import Path

import omni.usd
import omni.kit.app
from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file

BASE = Path(__file__).resolve().parents[1]
STAGE = BASE / "stages" / "trident_lakehouse_twin_replay.usda"
OUT_DIR = BASE / "docs" / "screenshots"

CAMERAS = [
    "Top_Overview",
    "Top_Ingest",
    "Top_RawBucket",
    "Top_Accumulation",
    "Top_Lakehouse",
    "Top_Staging",
    "Top_Search",
    "Top_Delivery",
    "Top_Tower",
]


def pump(n: int = 60) -> None:
    app = omni.kit.app.get_app()
    for _ in range(n):
        app.update()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    ctx = omni.usd.get_context()
    ctx.open_stage(str(STAGE))
    pump(120)  # let stage finish loading

    viewport = get_active_viewport()
    try:
        viewport.set_texture_resolution((1920, 1080))
    except Exception:
        pass

    for name in CAMERAS:
        cam_path = f"/World/Cameras/{name}"
        print(f"-> {cam_path}")
        viewport.camera_path = cam_path
        # Let the renderer catch up to the new camera + lighting
        pump(60)
        out_path = OUT_DIR / f"{name}.png"
        capture_viewport_to_file(viewport, str(out_path), is_hdr=False)
        # Capture is async; pump until the file is on disk
        for _ in range(120):
            omni.kit.app.get_app().update()
            if out_path.exists() and out_path.stat().st_size > 0:
                break
        print(f"   wrote {out_path}  ({out_path.stat().st_size if out_path.exists() else 0} bytes)")


if __name__ == "__main__":
    main()
    simulation_app.close()
