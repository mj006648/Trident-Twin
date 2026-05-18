from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})

from pathlib import Path
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "stages" / "trident_lakehouse_twin.usda"

COLORS = {
    "floor": (0.06, 0.07, 0.08),
    "lake": (0.10, 0.25, 0.55),
    "lakehouse": (0.18, 0.38, 0.30),
    "pipeline": (0.12, 0.12, 0.12),
    "metadata_explain": (0.10, 0.35, 0.95),
    "metadata_share": (0.10, 0.65, 0.35),
    "operator": (0.95, 0.75, 0.25),
    "workload": (0.60, 0.35, 0.95),
    "dataset_raw": (0.55, 0.55, 0.55),
    "dataset_explained": (0.10, 0.35, 0.95),
    "dataset_shared": (0.10, 0.70, 0.35),
    "dataset_staged": (0.55, 0.30, 0.95),
    "dataset_served": (1.00, 0.72, 0.15),
}


def create_mat(stage, name, color):
    mat = UsdShade.Material.Define(stage, f"/World/Materials/{name}")
    shader = UsdShade.Shader.Define(stage, f"/World/Materials/{name}/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.55)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def cube(stage, path, name, pos, scale, material, entity_id=None, entity_type=None, stage_name=None):
    prim = UsdGeom.Cube.Define(stage, path)
    prim.CreateSizeAttr(1.0)
    xform = UsdGeom.XformCommonAPI(prim)
    xform.SetTranslate(Gf.Vec3d(*pos))
    xform.SetScale(Gf.Vec3f(*scale))
    UsdShade.MaterialBindingAPI(prim).Bind(material)
    p = prim.GetPrim()
    p.CreateAttribute("trident:name", Sdf.ValueTypeNames.String).Set(name)
    if entity_id:
        p.CreateAttribute("trident:entity_id", Sdf.ValueTypeNames.String).Set(entity_id)
    if entity_type:
        p.CreateAttribute("trident:entity_type", Sdf.ValueTypeNames.String).Set(entity_type)
    if stage_name:
        p.CreateAttribute("trident:stage", Sdf.ValueTypeNames.String).Set(stage_name)
    return prim


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(OUT))
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(150)
    stage.SetTimeCodesPerSecond(24)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    UsdGeom.Xform.Define(stage, "/World")
    UsdGeom.Scope.Define(stage, "/World/Materials")
    UsdGeom.Scope.Define(stage, "/World/Environment")
    UsdGeom.Scope.Define(stage, "/World/Lake")
    UsdGeom.Scope.Define(stage, "/World/AccumulationPipeline")
    UsdGeom.Scope.Define(stage, "/World/Metadata")
    UsdGeom.Scope.Define(stage, "/World/Lakehouse")
    UsdGeom.Scope.Define(stage, "/World/WorkloadInterfaces")
    UsdGeom.Scope.Define(stage, "/World/Operations")
    UsdGeom.Scope.Define(stage, "/World/Datasets")

    mats = {k: create_mat(stage, k, v) for k, v in COLORS.items()}

    cube(stage, "/World/Environment/Floor", "Twin Floor", (0, 0, -0.05), (12, 5, 0.05), mats["floor"])

    # Conceptual lake/lakehouse zones
    cube(stage, "/World/Lake/BronzeLake", "Bronze Lake", (-6.3, 0, 0.5), (2.2, 2.0, 1.0), mats["lake"], "lake.bronze", "storage_zone", "accumulation")
    cube(stage, "/World/Lakehouse/SilverLakehouse", "Silver Lakehouse", (5.4, 0, 0.8), (2.0, 2.2, 1.6), mats["lakehouse"], "lakehouse.silver", "storage_zone", "staging")
    cube(stage, "/World/Lakehouse/StagingShelf1", "Staging Shelf 1", (5.4, -0.8, 1.7), (2.3, 0.10, 0.08), mats["pipeline"], "shelf.silver.1", "staging_shelf", "staging")
    cube(stage, "/World/Lakehouse/StagingShelf2", "Staging Shelf 2", (5.4, 0.0, 2.1), (2.3, 0.10, 0.08), mats["pipeline"], "shelf.silver.2", "staging_shelf", "staging")
    cube(stage, "/World/Lakehouse/StagingShelf3", "Staging Shelf 3", (5.4, 0.8, 2.5), (2.3, 0.10, 0.08), mats["pipeline"], "shelf.silver.3", "staging_shelf", "staging")

    # Pipelines and stations
    cube(stage, "/World/AccumulationPipeline/InputConveyor", "Accumulation Conveyor", (-4.2, 0, 0.18), (4.6, 0.18, 0.12), mats["pipeline"], "pipeline.accumulation", "pipeline", "accumulation")
    cube(stage, "/World/Metadata/ExplainingStation", "Explaining Metadata Station", (-2.4, 0, 0.6), (0.8, 1.4, 1.2), mats["metadata_explain"], "station.metadata.explaining", "metadata_station", "explaining")
    cube(stage, "/World/Metadata/SharingStation", "Sharing Metadata Station", (0.8, 0, 0.6), (0.8, 1.4, 1.2), mats["metadata_share"], "station.metadata.sharing", "metadata_station", "sharing")
    cube(stage, "/World/AccumulationPipeline/ToLakehouseConveyor", "To Lakehouse Conveyor", (2.8, 0, 0.18), (3.8, 0.18, 0.12), mats["pipeline"], "pipeline.to_lakehouse", "pipeline", "staging")

    # Operations and workload interfaces
    cube(stage, "/World/Operations/OperatorDesk", "Operator Desk", (1.4, -2.4, 0.55), (1.0, 0.7, 1.1), mats["operator"], "operator.control", "operator", "monitoring")
    cube(stage, "/World/WorkloadInterfaces/HPC", "HPC Interface", (7.8, -2.1, 0.7), (0.7, 0.7, 1.4), mats["workload"], "workload.hpc.001", "workload_interface", "serving")
    cube(stage, "/World/WorkloadInterfaces/MS", "M&S Interface", (8.8, -0.7, 0.7), (0.7, 0.7, 1.4), mats["workload"], "workload.ms.001", "workload_interface", "serving")
    cube(stage, "/World/WorkloadInterfaces/AI", "AI Interface", (8.8, 0.7, 0.7), (0.7, 0.7, 1.4), mats["workload"], "workload.ai.001", "workload_interface", "serving")
    cube(stage, "/World/WorkloadInterfaces/HPDA", "HPDA Interface", (7.8, 2.1, 0.7), (0.7, 0.7, 1.4), mats["workload"], "workload.hpda.001", "workload_interface", "serving")

    # Dataset package and small metadata tags
    dataset = cube(stage, "/World/Datasets/DatasetPackage001", "Dataset Package 001", (-9.0, 0, 0.7), (0.55, 0.38, 0.38), mats["dataset_raw"], "dataset.sample.001", "dataset", "raw")
    dataset.GetPrim().CreateAttribute("trident:metadata_status", Sdf.ValueTypeNames.String).Set("none")
    dataset.GetPrim().CreateAttribute("trident:sharing_status", Sdf.ValueTypeNames.String).Set("private")
    dataset.GetPrim().CreateAttribute("trident:quality_score", Sdf.ValueTypeNames.Float).Set(0.71)
    dataset.GetPrim().CreateAttribute("trident:access_frequency", Sdf.ValueTypeNames.Int).Set(0)

    cube(stage, "/World/Datasets/DatasetPackage001/ExplainingMetadataTag", "Explaining Metadata Tag", (0, 0.48, 0.42), (0.28, 0.05, 0.20), mats["metadata_explain"], "metadata.explaining.dataset.sample.001", "metadata", "explaining")
    cube(stage, "/World/Datasets/DatasetPackage001/SharingMetadataTag", "Sharing Metadata Tag", (0, -0.48, 0.42), (0.28, 0.05, 0.20), mats["metadata_share"], "metadata.sharing.dataset.sample.001", "metadata", "sharing")

    # Camera and light
    light = UsdGeom.Sphere.Define(stage, "/World/Environment/LightMarker")
    light.CreateRadiusAttr(0.2)
    UsdGeom.XformCommonAPI(light).SetTranslate(Gf.Vec3d(0, -3, 6))

    cam = UsdGeom.Camera.Define(stage, "/World/Camera")
    UsdGeom.XformCommonAPI(cam).SetTranslate(Gf.Vec3d(0, -10, 7))
    UsdGeom.XformCommonAPI(cam).SetRotate(Gf.Vec3f(58, 0, 0))
    cam.CreateFocalLengthAttr(24)
    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    stage.GetRootLayer().Save()
    print(f"created {OUT}")


if __name__ == "__main__":
    main()
    simulation_app.close()
