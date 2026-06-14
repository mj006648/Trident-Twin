"""Open the latest generated Trident Twin USD inside a running Kit/Isaac app.

Intended for Isaac Sim streaming startup:
  ./runheadless.sh --ext-folder /mnt/Trident-Twin-520d314/exts \
    --enable trident.twin --exec /mnt/Trident-Twin-520d314/scripts/open_latest_scene_streaming.py
"""
from __future__ import annotations

import os
import time
from pathlib import Path

import carb
import omni.kit.app
import omni.usd

BASE = Path(__file__).resolve().parents[1]
STAGES_DIR = BASE / "stages"
DEFAULT_CAMERA = os.getenv("TRIDENT_TWIN_DEFAULT_CAMERA", "/World/Cameras/Overview_Top45")


def _latest_usda() -> Path:
    files = sorted(
        p for p in STAGES_DIR.glob("trident_lakehouse_twin_*.usda")
        if "replay" not in p.name and p.stat().st_size > 1024
    )
    if not files:
        raise FileNotFoundError(f"No generated Trident Twin USD found in {STAGES_DIR}")
    return files[-1]


def _pump(frames: int = 120) -> None:
    app = omni.kit.app.get_app()
    for _ in range(frames):
        app.update()


def main() -> None:
    stage_path = Path(os.getenv("SCENE_PATH", "") or _latest_usda())
    carb.log_info(f"[trident.twin] opening latest scene: {stage_path}")
    ctx = omni.usd.get_context()
    ctx.open_stage(str(stage_path))
    _pump(180)
    stage = ctx.get_stage()
    if stage is None:
        raise RuntimeError(f"Failed to open stage: {stage_path}")

    # Set an overview camera so the livestream starts with a useful view.
    if stage.GetPrimAtPath(DEFAULT_CAMERA).IsValid():
        try:
            from omni.kit.viewport.utility import get_active_viewport
            viewport = get_active_viewport()
            if viewport:
                viewport.camera_path = DEFAULT_CAMERA
        except Exception as exc:  # viewport utility can be unavailable in no-window mode
            carb.log_warn(f"[trident.twin] viewport camera set failed: {exc}")
            carb.settings.get_settings().set("/app/viewport/defaultCameraPath", DEFAULT_CAMERA)
    carb.log_info(f"[trident.twin] scene ready: {stage_path.name}")


main()
