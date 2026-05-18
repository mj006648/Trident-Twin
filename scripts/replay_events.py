from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})

import json
from pathlib import Path
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

BASE = Path(__file__).resolve().parents[1]
IN_STAGE = BASE / "stages" / "trident_lakehouse_twin.usda"
OUT_STAGE = BASE / "stages" / "trident_lakehouse_twin_replay.usda"
EVENTS = BASE / "data" / "mock_twin_events.json"

COLOR_TO_MATERIAL = {
    "raw": "/World/Materials/dataset_raw",
    "explained": "/World/Materials/dataset_explained",
    "shared": "/World/Materials/dataset_shared",
    "staged": "/World/Materials/dataset_staged",
    "requested": "/World/Materials/dataset_staged",
    "served": "/World/Materials/dataset_served",
}


def copy_base_stage():
    if not IN_STAGE.exists():
        raise FileNotFoundError(f"Base stage missing: {IN_STAGE}. Run scripts/create_scene.py first.")
    OUT_STAGE.write_text(IN_STAGE.read_text(), encoding="utf-8")


def main():
    copy_base_stage()
    with EVENTS.open("r", encoding="utf-8") as f:
        data = json.load(f)
    timeline = data["timeline"]

    stage = Usd.Stage.Open(str(OUT_STAGE))
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(max(e["time"] for e in timeline))
    stage.SetTimeCodesPerSecond(24)

    dataset = stage.GetPrimAtPath("/World/Datasets/DatasetPackage001")
    if not dataset:
        raise RuntimeError("DatasetPackage001 prim not found")

    xform = UsdGeom.XformCommonAPI(dataset)
    stage_attr = dataset.GetAttribute("trident:stage") or dataset.CreateAttribute("trident:stage", Sdf.ValueTypeNames.String)
    zone_attr = dataset.GetAttribute("trident:zone") or dataset.CreateAttribute("trident:zone", Sdf.ValueTypeNames.String)
    metadata_attr = dataset.GetAttribute("trident:metadata_status") or dataset.CreateAttribute("trident:metadata_status", Sdf.ValueTypeNames.String)
    sharing_attr = dataset.GetAttribute("trident:sharing_status") or dataset.CreateAttribute("trident:sharing_status", Sdf.ValueTypeNames.String)
    access_attr = dataset.GetAttribute("trident:access_frequency") or dataset.CreateAttribute("trident:access_frequency", Sdf.ValueTypeNames.Int)
    event_attr = dataset.GetAttribute("trident:last_event") or dataset.CreateAttribute("trident:last_event", Sdf.ValueTypeNames.String)

    for event in timeline:
        t = Usd.TimeCode(event["time"])
        xform.SetTranslate(Gf.Vec3d(*event["position"]), t)
        stage_attr.Set(event["stage"], t)
        zone_attr.Set(event["zone"], t)
        metadata_attr.Set(event.get("metadata_status", "none"), t)
        sharing_attr.Set(event.get("sharing_status", "private"), t)
        access_attr.Set(int(event.get("access_frequency", 0)), t)
        event_attr.Set(event["event"], t)

    # Static material binding uses final/served material. Runtime extension can switch material per event.
    mat_path = COLOR_TO_MATERIAL[timeline[-1].get("color", "served")]
    mat = UsdShade.Material(stage.GetPrimAtPath(mat_path))
    UsdShade.MaterialBindingAPI(dataset).Bind(mat)

    stage.GetRootLayer().Save()
    print(f"created {OUT_STAGE}")
    print("timeline:")
    for event in timeline:
        print(f"  t={event['time']:>3} {event['event']} -> {event['stage']} @ {event['position']}")


if __name__ == "__main__":
    main()
    simulation_app.close()
