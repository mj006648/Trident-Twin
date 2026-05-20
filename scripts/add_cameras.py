"""Add demo camera presets to the Trident Twin USD stages.

Adds five cameras under /World/Cameras that match the 3-minute demo scenario
described in docs/master-plan.md (section 7).

Run after scripts/create_scene.py (and optionally scripts/replay_events.py):

    /home/chang/isaac-sim/python.sh scripts/add_cameras.py

This script is idempotent: existing cameras at the same paths are overwritten.

Coordinate context (matches scripts/create_scene.py):
    X axis: data flow direction, BronzeLake at x=-6.3, SilverLakehouse at x=+5.4
    Y axis: lateral, OperatorDesk at y=-2.4, workload docks at y=+/-2.1
    Z axis: vertical, floor at z=0, shelves up to z=2.5
    Up axis: Z, units: meters
"""
from isaacsim import SimulationApp  # type: ignore

simulation_app = SimulationApp({"headless": True})

from pathlib import Path

from pxr import Gf, Usd, UsdGeom, Sdf

BASE = Path(__file__).resolve().parents[1]
STAGES = [
    BASE / "stages" / "trident_lakehouse_twin.usda",
    BASE / "stages" / "trident_lakehouse_twin_replay.usda",
]

# (path, translate, rotateXYZ, focal_length_mm, label, narration)
PRESETS = [
    (
        "/World/Cameras/Cam00_Aerial",
        (0.0, -2.0, 16.0),
        (75.0, 0.0, 0.0),
        20.0,
        "00 Aerial Overview",
        "Trident Lakehouse 전경. 좌측 Lake, 중앙 Metadata, 우측 Lakehouse + Workload Docks.",
    ),
    (
        "/World/Cameras/Cam01_Accumulation",
        (-3.5, -6.5, 4.0),
        (62.0, 0.0, -25.0),
        28.0,
        "01 Accumulation Pipeline",
        "Dataset Package가 Bronze Lake에서 Explaining/Sharing Station을 거쳐 Silver Lakehouse로 흘러갑니다.",
    ),
    (
        "/World/Cameras/Cam02_Metadata",
        (-0.8, -4.2, 3.0),
        (60.0, 0.0, 0.0),
        35.0,
        "02 Metadata Stations",
        "Explaining Station은 Milvus Super Context를, Sharing Station은 Redis 위치 메타를 발급합니다.",
    ),
    (
        "/World/Cameras/Cam03_Delivery",
        (6.5, -5.5, 3.5),
        (60.0, 0.0, 28.0),
        28.0,
        "03 Delivery Docks",
        "Staging Shelf에서 AI/HPC/HPDA/MS 도크로 데이터셋이 진열·전달됩니다.",
    ),
    (
        "/World/Cameras/Cam04_Operator",
        (1.4, -5.0, 2.2),
        (68.0, 0.0, 0.0),
        35.0,
        "04 Operator Desk",
        "운영자는 trident:* 속성과 이벤트 타임라인으로 모든 상태를 추적합니다.",
    ),
]


def add_cameras(stage_path: Path) -> None:
    if not stage_path.exists():
        print(f"skip (missing): {stage_path}")
        return
    stage = Usd.Stage.Open(str(stage_path))
    UsdGeom.Scope.Define(stage, "/World/Cameras")
    for path, translate, rotate, focal, label, narration in PRESETS:
        cam = UsdGeom.Camera.Define(stage, path)
        xform = UsdGeom.XformCommonAPI(cam)
        xform.SetTranslate(Gf.Vec3d(*translate))
        xform.SetRotate(Gf.Vec3f(*rotate))
        cam.CreateFocalLengthAttr(focal)
        cam.CreateClippingRangeAttr(Gf.Vec2f(0.1, 1000.0))
        prim = cam.GetPrim()
        prim.CreateAttribute("trident:camera_label", Sdf.ValueTypeNames.String).Set(label)
        prim.CreateAttribute("trident:camera_narration", Sdf.ValueTypeNames.String).Set(narration)
    stage.GetRootLayer().Save()
    print(f"updated cameras in {stage_path.name}")


def main() -> None:
    for stage_path in STAGES:
        add_cameras(stage_path)


if __name__ == "__main__":
    main()
    simulation_app.close()
