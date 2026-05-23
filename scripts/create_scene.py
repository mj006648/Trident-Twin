"""
Trident-Twin v3 scene generator.

Key design moves from v2.5:
  - No signposts / no rooftop banners. Each zone is identified by a colored
    floor pad slab directly beneath it.
  - Raw Bucket / Lakehouse / Showcase are all the SAME size (10 x 7 x 5).
  - Lakehouse and Showcase are placed SIDE-BY-SIDE on the Y axis
    (Lakehouse at Y=-7, Showcase at Y=+7) — same X range, parallel.
  - Lakehouse interior: simple storage tables with iceberg boxes on top.
  - Showcase interior: real glass display cabinets with spotlit boxes
    (no more pedestal cylinders).
  - Two separate delivery conveyor trunks:
      * COLD trunk (Lakehouse -> 3 docks, runs along Y=-9)
      * HOT  trunk (Showcase  -> 3 docks, runs along Y=+9)
    Each dock receives both belts.
  - Promotion belt connects Lakehouse to Showcase (Y axis belt between them).
  - Zone 0 Lobby relocated next to Control Tower at the far south-west.
"""

from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})

from pathlib import Path
from pxr import Usd, UsdGeom, UsdShade, UsdLux, Sdf, Gf

BASE = Path(__file__).resolve().parents[1]
OUT = BASE / "stages" / "trident_lakehouse_twin.usda"

# ============================================================================
# Material palette
# ============================================================================
COLORS = {
    "floor":              ((0.16, 0.18, 0.20), 1.00),
    "concrete":           ((0.42, 0.43, 0.45), 1.00),
    "asphalt":            ((0.12, 0.13, 0.14), 1.00),
    "steel_frame":        ((0.08, 0.09, 0.11), 1.00),
    "white_panel":        ((0.94, 0.95, 0.97), 1.00),
    "black_panel":        ((0.05, 0.05, 0.05), 1.00),
    # Glass tints
    "glass_lake":         ((0.10, 0.40, 0.85), 0.14),
    "glass_lakehouse":    ((0.20, 0.70, 0.50), 0.14),
    "glass_showcase":     ((0.95, 0.80, 0.20), 0.18),
    "glass_office":       ((0.55, 0.75, 0.95), 0.18),
    "glass_tower":        ((0.30, 0.50, 0.80), 0.20),
    "glass_lobby":        ((0.20, 0.80, 0.85), 0.20),
    "glass_display":      ((0.92, 0.95, 0.98), 0.18),  # case glass (subtle white)
    # Zone floor-pad colors
    "zone_color_0":       ((0.18, 0.85, 0.90), 1.00),  # cyan - lobby
    "zone_color_1":       ((0.95, 0.55, 0.05), 1.00),  # orange - truck yard
    "zone_color_2":       ((0.55, 0.35, 0.15), 1.00),  # brown - raw bucket
    "zone_color_3":       ((0.95, 0.85, 0.10), 1.00),  # yellow - pipeline
    "zone_color_35":      ((0.95, 0.20, 0.20), 1.00),  # red - audit gate
    "zone_color_4":       ((0.20, 0.75, 0.55), 1.00),  # teal - lakehouse
    "zone_color_5":       ((1.00, 0.75, 0.15), 1.00),  # gold - showcase
    "zone_color_6":       ((0.40, 0.65, 0.95), 1.00),  # sky blue - catalog
    "zone_color_7":       ((0.55, 0.25, 0.85), 1.00),  # purple - search
    "zone_color_8":       ((0.65, 0.45, 0.95), 1.00),  # violet - delivery
    "zone_color_9":       ((0.30, 0.50, 0.80), 1.00),  # navy - tower
    # Conveyor / industrial
    "conveyor_belt":      ((0.10, 0.10, 0.12), 1.00),
    "conveyor_belt_express": ((0.18, 0.18, 0.22), 1.00),
    "conveyor_roller":    ((0.55, 0.55, 0.58), 1.00),
    "conveyor_frame":     ((0.95, 0.55, 0.05), 1.00),
    "conveyor_hot":       ((0.95, 0.25, 0.10), 1.00),
    "conveyor_cold":      ((0.20, 0.65, 0.95), 1.00),
    "conveyor_promotion": ((0.95, 0.50, 0.95), 1.00),
    # Metallic theme colors used to mark data lifecycle stages
    "metal_bronze":       ((0.72, 0.45, 0.22), 1.00),  # Raw stage
    "metal_silver":       ((0.78, 0.80, 0.84), 1.00),  # Pipeline + Lakehouse
    "metal_gold":         ((0.98, 0.78, 0.18), 1.00),  # Showcase
    # Truck
    "truck_cab":          ((0.85, 0.20, 0.20), 1.00),
    "truck_trailer":      ((0.92, 0.92, 0.94), 1.00),
    "truck_wheel":        ((0.05, 0.05, 0.05), 1.00),
    "truck_window":       ((0.10, 0.15, 0.25), 1.00),
    # Vehicle variants
    "ai_truck":           ((0.10, 0.65, 0.30), 1.00),
    "ai_truck_accent":    ((0.55, 1.00, 0.20), 1.00),
    "hpc_van":            ((0.55, 0.56, 0.60), 1.00),
    "hpc_van_accent":     ((0.40, 0.40, 0.45), 1.00),
    "hpda_van":           ((0.15, 0.25, 0.55), 1.00),
    "hpda_van_accent":    ((0.45, 0.70, 0.95), 1.00),
    # Boxes
    "raw_box":            ((0.42, 0.28, 0.16), 1.00),
    "raw_box_dark":       ((0.32, 0.20, 0.12), 1.00),
    "iceberg_box":        ((0.94, 0.95, 0.97), 1.00),
    "milvus_label":       ((0.55, 0.25, 0.85), 1.00),
    "redis_card":         ((0.85, 0.18, 0.20), 1.00),
    "led_green":          ((0.20, 0.95, 0.30), 1.00),
    "led_yellow":         ((0.95, 0.85, 0.20), 1.00),
    "led_red":            ((0.95, 0.20, 0.20), 1.00),
    # Furniture / storage
    "table_top":          ((0.55, 0.40, 0.20), 1.00),
    "table_leg":          ((0.18, 0.13, 0.08), 1.00),
    "display_base":       ((0.18, 0.18, 0.20), 1.00),
    "display_cap":        ((0.10, 0.10, 0.12), 1.00),
    # Pipeline stations
    "machine_probing":    ((0.85, 0.85, 0.20), 1.00),
    "machine_architect":  ((0.10, 0.85, 0.95), 1.00),
    "machine_iceberg":    ((0.95, 0.95, 1.00), 1.00),
    "machine_milvus":     ((0.55, 0.25, 0.85), 1.00),
    "machine_redis":      ((0.85, 0.18, 0.20), 1.00),
    "machine_explain":    ((0.10, 0.35, 0.95), 1.00),
    "machine_share":      ((0.10, 0.65, 0.35), 1.00),
    "scanner_red":        ((1.00, 0.20, 0.15), 1.00),
    "scanner_beam":       ((1.00, 0.20, 0.15), 0.35),
    "audit_pass":         ((0.20, 0.95, 0.30), 1.00),
    "audit_fail":         ((0.95, 0.20, 0.20), 1.00),
    # Showcase visual
    "spotlight_beam":     ((1.00, 0.95, 0.60), 0.22),
    "popularity_star":    ((1.00, 0.85, 0.10), 1.00),
    # Indicators
    "indicator_milvus":   ((0.55, 0.25, 0.85), 1.00),
    "indicator_llm":      ((0.95, 0.55, 0.10), 1.00),
    "indicator_redis":    ((0.85, 0.18, 0.20), 1.00),
    "indicator_off":      ((0.25, 0.25, 0.27), 1.00),
    # Operator
    "operator":           ((0.95, 0.75, 0.25), 1.00),
    "monitor_screen":     ((0.10, 0.45, 0.95), 1.00),
    "workload":           ((0.60, 0.35, 0.95), 1.00),
    "gpu_logo":           ((0.20, 0.85, 0.35), 1.00),
    # Avatar roles
    "role_admin":         ((1.00, 0.80, 0.10), 1.00),
    "role_operator":      ((0.15, 0.40, 0.80), 1.00),
    "role_researcher":    ((0.96, 0.96, 0.98), 1.00),
    "role_viewer":        ((0.55, 0.55, 0.58), 1.00),
    "role_service":       ((0.25, 0.25, 0.27), 1.00),
    "skin_tone":          ((0.85, 0.75, 0.65), 1.00),
    "badge_text":         ((0.10, 0.10, 0.12), 1.00),
    # Lineage rays
    "lineage_table":      ((0.95, 0.95, 0.95), 0.45),
    "lineage_column":     ((0.55, 0.25, 0.85), 0.45),
    "lineage_impact":     ((1.00, 0.85, 0.10), 0.65),
    # Legacy / replay
    "metadata_explain":   ((0.10, 0.35, 0.95), 1.00),
    "metadata_share":     ((0.10, 0.65, 0.35), 1.00),
    "dataset_raw":        ((0.42, 0.28, 0.16), 1.00),
    "dataset_explained":  ((0.10, 0.35, 0.95), 1.00),
    "dataset_shared":     ((0.10, 0.70, 0.35), 1.00),
    "dataset_staged":     ((0.55, 0.30, 0.95), 1.00),
    "dataset_served":     ((1.00, 0.72, 0.15), 1.00),
}


# ============================================================================
# Primitive helpers
# ============================================================================
def create_mat(stage, name, color, opacity):
    mat = UsdShade.Material.Define(stage, f"/World/Materials/{name}")
    shader = UsdShade.Shader.Define(stage, f"/World/Materials/{name}/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*color))
    shader.CreateInput("roughness", Sdf.ValueTypeNames.Float).Set(0.45)
    shader.CreateInput("metallic", Sdf.ValueTypeNames.Float).Set(0.0)
    if opacity < 1.0:
        shader.CreateInput("opacity", Sdf.ValueTypeNames.Float).Set(opacity)
        shader.CreateInput("opacityThreshold", Sdf.ValueTypeNames.Float).Set(0.0)
    mat.CreateSurfaceOutput().ConnectToSource(shader.ConnectableAPI(), "surface")
    return mat


def cube(stage, path, pos, scale, material,
         name=None, entity_id=None, entity_type=None, stage_name=None):
    prim = UsdGeom.Cube.Define(stage, path)
    prim.CreateSizeAttr(1.0)
    xform = UsdGeom.XformCommonAPI(prim)
    xform.SetTranslate(Gf.Vec3d(*pos))
    xform.SetScale(Gf.Vec3f(*scale))
    UsdShade.MaterialBindingAPI(prim).Bind(material)
    p = prim.GetPrim()
    if name is not None:
        p.CreateAttribute("trident:name", Sdf.ValueTypeNames.String).Set(name)
    if entity_id is not None:
        p.CreateAttribute("trident:entity_id", Sdf.ValueTypeNames.String).Set(entity_id)
    if entity_type is not None:
        p.CreateAttribute("trident:entity_type", Sdf.ValueTypeNames.String).Set(entity_type)
    if stage_name is not None:
        p.CreateAttribute("trident:stage", Sdf.ValueTypeNames.String).Set(stage_name)
    return prim


def cyl(stage, path, pos, radius, height, axis, material):
    prim = UsdGeom.Cylinder.Define(stage, path)
    prim.CreateRadiusAttr(radius)
    prim.CreateHeightAttr(height)
    prim.CreateAxisAttr(axis)
    UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(*pos))
    UsdShade.MaterialBindingAPI(prim).Bind(material)
    return prim


def sphere(stage, path, pos, radius, material):
    prim = UsdGeom.Sphere.Define(stage, path)
    prim.CreateRadiusAttr(radius)
    UsdGeom.XformCommonAPI(prim).SetTranslate(Gf.Vec3d(*pos))
    UsdShade.MaterialBindingAPI(prim).Bind(material)
    return prim


def zone_pad(stage, path, center, size, color_mat):
    """Colored floor slab marking the zone footprint (no signposts)."""
    cx, cy = center
    sx, sy = size
    cube(stage, path, (cx, cy, 0.012), (sx, sy, 0.024), color_mat)


# ============================================================================
# Box helpers
# ============================================================================
def make_raw_box(stage, path, pos, scale, mats, dark=False):
    mat = mats["raw_box_dark"] if dark else mats["raw_box"]
    return cube(stage, path, pos, scale, mat)


def make_iceberg_box(stage, path, pos, scale, mats, led="green"):
    UsdGeom.Xform.Define(stage, path)
    sx, sy, sz = scale
    cube(stage, f"{path}/Body", pos, scale, mats["iceberg_box"])
    label_t = 0.015
    cube(stage, f"{path}/MilvusLabel",
         (pos[0], pos[1] + sy / 2 + label_t, pos[2]),
         (sx * 0.65, label_t * 2, sz * 0.42), mats["milvus_label"])
    cube(stage, f"{path}/RedisCard",
         (pos[0] + sx * 0.20, pos[1], pos[2] + sz / 2 + 0.012),
         (sx * 0.42, sy * 0.55, 0.025), mats["redis_card"])
    led_mat = {"green": mats["led_green"], "yellow": mats["led_yellow"],
               "red": mats["led_red"]}[led]
    cyl(stage, f"{path}/LED",
        (pos[0] - sx * 0.30, pos[1] - sy * 0.30, pos[2] + sz / 2 + 0.018),
        0.025, 0.025, "Z", led_mat)


# ============================================================================
# Storage table (Lakehouse interior)
# ============================================================================
def build_storage_table(stage, root_path, center, mats, n_boxes=2, leds=None):
    """Simple warehouse table with N labeled boxes on top."""
    UsdGeom.Scope.Define(stage, root_path)
    cx, cy = center
    floor_z = 0.10
    table_w = 1.7
    table_d = 0.95
    table_top_z = 0.85  # height to underside of tabletop
    leg_h = 0.80
    leg_w = 0.08
    for sxs, sys_, lbl in [(-1, -1, "SW"), (-1, +1, "NW"),
                           (+1, -1, "SE"), (+1, +1, "NE")]:
        cube(stage, f"{root_path}/Leg_{lbl}",
             (cx + sxs * (table_w / 2 - leg_w / 2),
              cy + sys_ * (table_d / 2 - leg_w / 2),
              floor_z + leg_h / 2),
             (leg_w, leg_w, leg_h), mats["table_leg"])
    cube(stage, f"{root_path}/Top", (cx, cy, floor_z + table_top_z),
         (table_w, table_d, 0.06), mats["table_top"])
    if leds is None:
        leds = ["green"] * n_boxes
    if n_boxes > 0:
        box_spacing = table_w / n_boxes
        for i in range(n_boxes):
            bx = cx - table_w / 2 + (i + 0.5) * box_spacing
            make_iceberg_box(stage, f"{root_path}/Box_{i + 1}",
                             (bx, cy, floor_z + table_top_z + 0.05 + 0.20),
                             (0.50, 0.36, 0.40), mats, led=leds[i % len(leds)])


# ============================================================================
# Display case (Showcase interior)
# ============================================================================
def build_display_case(stage, root_path, center, mats, popularity=4):
    """Tall vertical glass display cabinet with a spotlit box inside."""
    UsdGeom.Scope.Define(stage, root_path)
    cx, cy = center
    floor_z = 0.10
    base_h = 0.35
    cap_h = 0.15
    case_w = 1.0
    case_d = 0.8
    case_h = 1.85
    # Base
    cube(stage, f"{root_path}/Base", (cx, cy, floor_z + base_h / 2),
         (case_w, case_d, base_h), mats["display_base"])
    # Cap
    cube(stage, f"{root_path}/Cap",
         (cx, cy, floor_z + case_h - cap_h / 2),
         (case_w, case_d, cap_h), mats["display_cap"])
    # Glass walls
    wt = 0.025
    inner_h = case_h - base_h - cap_h
    inner_z = floor_z + base_h + inner_h / 2
    cube(stage, f"{root_path}/Glass_Left",
         (cx - case_w / 2 + wt / 2, cy, inner_z),
         (wt, case_d, inner_h), mats["glass_display"])
    cube(stage, f"{root_path}/Glass_Right",
         (cx + case_w / 2 - wt / 2, cy, inner_z),
         (wt, case_d, inner_h), mats["glass_display"])
    cube(stage, f"{root_path}/Glass_Front",
         (cx, cy - case_d / 2 + wt / 2, inner_z),
         (case_w, wt, inner_h), mats["glass_display"])
    cube(stage, f"{root_path}/Glass_Back",
         (cx, cy + case_d / 2 - wt / 2, inner_z),
         (case_w, wt, inner_h), mats["glass_display"])
    # Featured iceberg box inside, slightly elevated
    box_z = floor_z + base_h + 0.30
    make_iceberg_box(stage, f"{root_path}/Box",
                     (cx, cy, box_z), (0.55, 0.40, 0.40), mats)
    # Spotlight beam inside the case
    cyl(stage, f"{root_path}/SpotlightBeam",
        (cx, cy, floor_z + base_h + inner_h * 0.55),
        case_w * 0.30, inner_h * 0.85, "Z", mats["spotlight_beam"])
    # Plaque on front of base
    cube(stage, f"{root_path}/Plaque",
         (cx, cy - case_d / 2 - 0.012, floor_z + base_h / 2 + 0.05),
         (case_w * 0.85, 0.025, 0.12), mats["popularity_star"])
    # Popularity stars row below plaque
    for i in range(popularity):
        cyl(stage, f"{root_path}/Star_{i + 1}",
            (cx - 0.25 + i * 0.12,
             cy - case_d / 2 - 0.018,
             floor_z + base_h / 2 - 0.08),
            0.04, 0.025, "Y", mats["popularity_star"])


# ============================================================================
# Living-room style display cabinet (wide wooden showcase with glass front)
# ============================================================================
def build_showcase_cabinet(stage, root_path, cx, cy, mats,
                            cab_w=4.0, cab_d=0.7, cab_h=2.4,
                            facing="south", popularity=4):
    """Wooden display cabinet with 3 shelves of items behind a glass door.
    facing: which direction the glass front faces ('south' = -Y, 'north' = +Y)."""
    UsdGeom.Scope.Define(stage, root_path)
    floor_z = 0.10
    sign_y = -1 if facing == "south" else +1
    # Solid wooden base
    base_h = 0.30
    cube(stage, f"{root_path}/Base", (cx, cy, floor_z + base_h / 2),
         (cab_w, cab_d, base_h), mats["table_top"])
    # Top crown / trim
    crown_h = 0.18
    cube(stage, f"{root_path}/Crown",
         (cx, cy, floor_z + cab_h - crown_h / 2),
         (cab_w + 0.25, cab_d + 0.10, crown_h), mats["table_top"])
    # Corner posts
    pw = 0.10
    for sxs, sys_, lbl in [(-1, -1, "SW"), (-1, +1, "NW"),
                           (+1, -1, "SE"), (+1, +1, "NE")]:
        cube(stage, f"{root_path}/Post_{lbl}",
             (cx + sxs * (cab_w / 2 - pw / 2),
              cy + sys_ * (cab_d / 2 - pw / 2),
              floor_z + cab_h / 2),
             (pw, pw, cab_h), mats["table_top"])
    # Vertical wooden dividers (creates a 3-section look)
    div_w = 0.08
    div_h = cab_h - base_h - crown_h - 0.05
    for x_off in [-cab_w / 3, +cab_w / 3]:
        cube(stage, f"{root_path}/Divider_{'L' if x_off < 0 else 'R'}",
             (cx + x_off, cy + sign_y * (cab_d / 2 - div_w / 2),
              floor_z + base_h + div_h / 2),
             (div_w, div_w + 0.02, div_h), mats["table_top"])
    # Glass front (one big translucent panel on the chosen facing)
    glass_t = 0.025
    cube(stage, f"{root_path}/GlassFront",
         (cx, cy + sign_y * (cab_d / 2 - glass_t / 2),
          floor_z + base_h + (cab_h - base_h - crown_h) / 2),
         (cab_w - 0.15, glass_t, cab_h - base_h - crown_h),
         mats["glass_display"])
    # 3 horizontal shelves
    shelf_zs = [floor_z + base_h + 0.10,
                floor_z + base_h + 0.80,
                floor_z + base_h + 1.50]
    n_items = 4
    for i, sz in enumerate(shelf_zs):
        cube(stage, f"{root_path}/Shelf_{i + 1}",
             (cx, cy, sz),
             (cab_w - 0.2, cab_d - 0.1, 0.04), mats["table_top"])
        for j in range(n_items):
            ix = cx - cab_w / 2 + 0.55 + j * (cab_w - 1.1) / (n_items - 1)
            led = "green" if (i + j) % 3 != 0 else ("yellow" if (i + j) % 2 == 0 else "red")
            make_iceberg_box(stage, f"{root_path}/Item_S{i + 1}_J{j + 1}",
                             (ix, cy, sz + 0.05 + 0.18),
                             (0.42, 0.30, 0.36), mats, led=led)
    # Spotlights tucked under the crown
    for j in range(3):
        bulb_x = cx - cab_w / 3 + j * cab_w / 3
        cyl(stage, f"{root_path}/Bulb_{j + 1}",
            (bulb_x, cy + sign_y * 0.12,
             floor_z + cab_h - crown_h - 0.05),
            0.06, 0.08, "Z", mats["led_yellow"])
    # Popularity stars on top of the base, in front of the glass
    for k in range(popularity):
        cyl(stage, f"{root_path}/Star_{k + 1}",
            (cx - 0.40 + k * 0.20,
             cy + sign_y * (cab_d / 2 + 0.05),
             floor_z + base_h + 0.04),
            0.07, 0.025, "Z", mats["popularity_star"])


# ============================================================================
# Warehouse (transparent glass + steel frame)
# ============================================================================
def build_warehouse(stage, root_path, center, size, wall_mat, frame_mat,
                    left_gap=None, right_gap=None,
                    front_gap=None, back_gap=None):
    cx, cy, cz = center
    sx, sy, sz = size
    UsdGeom.Scope.Define(stage, f"{root_path}/Frame")
    UsdGeom.Scope.Define(stage, f"{root_path}/Walls")

    pw = 0.18
    post_z = cz + sz / 2
    for sxs, sys_, lbl in [(-1, -1, "SW"), (-1, +1, "NW"),
                           (+1, -1, "SE"), (+1, +1, "NE")]:
        x = cx + sxs * (sx / 2 - pw / 2)
        y = cy + sys_ * (sy / 2 - pw / 2)
        cube(stage, f"{root_path}/Frame/Post_{lbl}",
             (x, y, post_z), (pw, pw, sz), frame_mat)

    bw = 0.14
    beam_z = cz + sz - bw / 2
    cube(stage, f"{root_path}/Frame/Beam_Front", (cx, cy - sy / 2 + bw / 2, beam_z),
         (sx, bw, bw), frame_mat)
    cube(stage, f"{root_path}/Frame/Beam_Back",  (cx, cy + sy / 2 - bw / 2, beam_z),
         (sx, bw, bw), frame_mat)
    cube(stage, f"{root_path}/Frame/Beam_Left",  (cx - sx / 2 + bw / 2, cy, beam_z),
         (bw, sy, bw), frame_mat)
    cube(stage, f"{root_path}/Frame/Beam_Right", (cx + sx / 2 - bw / 2, cy, beam_z),
         (bw, sy, bw), frame_mat)
    for i, frac in enumerate([0.25, 0.50, 0.75]):
        x = cx - sx / 2 + sx * frac
        cube(stage, f"{root_path}/Frame/Beam_Cross_{i + 1}", (x, cy, beam_z),
             (bw, sy, bw), frame_mat)

    wt = 0.05
    wall_z = cz + sz / 2

    def _x_wall(side_name, side_x, gap):
        if gap is None:
            cube(stage, f"{root_path}/Walls/{side_name}",
                 (side_x, cy, wall_z), (wt, sy, sz), wall_mat)
            return
        gy_c, gy_w, gz_t = gap
        above_h = sz - gz_t
        if above_h > 0.01:
            cube(stage, f"{root_path}/Walls/{side_name}_Above",
                 (side_x, cy, cz + gz_t + above_h / 2),
                 (wt, sy, above_h), wall_mat)
        ny_size = (cy + gy_c - gy_w / 2) - (cy - sy / 2)
        if ny_size > 0.01:
            cube(stage, f"{root_path}/Walls/{side_name}_NegY",
                 (side_x, cy - sy / 2 + ny_size / 2, cz + gz_t / 2),
                 (wt, ny_size, gz_t), wall_mat)
        py_start = cy + gy_c + gy_w / 2
        py_size = (cy + sy / 2) - py_start
        if py_size > 0.01:
            cube(stage, f"{root_path}/Walls/{side_name}_PosY",
                 (side_x, py_start + py_size / 2, cz + gz_t / 2),
                 (wt, py_size, gz_t), wall_mat)

    def _y_wall(side_name, side_y, gap):
        if gap is None:
            cube(stage, f"{root_path}/Walls/{side_name}",
                 (cx, side_y, wall_z), (sx, wt, sz), wall_mat)
            return
        gx_c, gx_w, gz_t = gap
        above_h = sz - gz_t
        if above_h > 0.01:
            cube(stage, f"{root_path}/Walls/{side_name}_Above",
                 (cx, side_y, cz + gz_t + above_h / 2),
                 (sx, wt, above_h), wall_mat)
        nx_size = (cx + gx_c - gx_w / 2) - (cx - sx / 2)
        if nx_size > 0.01:
            cube(stage, f"{root_path}/Walls/{side_name}_NegX",
                 (cx - sx / 2 + nx_size / 2, side_y, cz + gz_t / 2),
                 (nx_size, wt, gz_t), wall_mat)
        px_start = cx + gx_c + gx_w / 2
        px_size = (cx + sx / 2) - px_start
        if px_size > 0.01:
            cube(stage, f"{root_path}/Walls/{side_name}_PosX",
                 (px_start + px_size / 2, side_y, cz + gz_t / 2),
                 (px_size, wt, gz_t), wall_mat)

    _x_wall("Left",  cx - sx / 2, left_gap)
    _x_wall("Right", cx + sx / 2, right_gap)
    _y_wall("Front", cy - sy / 2, front_gap)
    _y_wall("Back",  cy + sy / 2, back_gap)


def build_glass_office(stage, root_path, center, size, wall_mat, frame_mat):
    build_warehouse(stage, root_path, center, size, wall_mat, frame_mat)


# ============================================================================
# Conveyors (X-axis and Y-axis variants)
# ============================================================================
def build_conveyor(stage, root_path, x_start, x_end, y_center, z_top, width, mats,
                   frame_mat_key="conveyor_frame", belt_mat_key="conveyor_belt"):
    UsdGeom.Scope.Define(stage, root_path)
    length = x_end - x_start
    if length <= 0:
        return
    center_x = (x_start + x_end) / 2
    belt_thickness = 0.06
    cube(stage, f"{root_path}/Belt",
         (center_x, y_center, z_top - belt_thickness / 2),
         (length, width, belt_thickness), mats[belt_mat_key])
    rail_h = 0.18
    rail_w = 0.05
    cube(stage, f"{root_path}/Rail_Y_neg",
         (center_x, y_center - width / 2 - rail_w / 2,
          z_top + rail_h / 4 - belt_thickness / 2),
         (length, rail_w, rail_h + belt_thickness), mats[frame_mat_key])
    cube(stage, f"{root_path}/Rail_Y_pos",
         (center_x, y_center + width / 2 + rail_w / 2,
          z_top + rail_h / 4 - belt_thickness / 2),
         (length, rail_w, rail_h + belt_thickness), mats[frame_mat_key])
    n_rollers = max(2, int(length / 0.8))
    for i in range(n_rollers):
        x = x_start + (i + 0.5) * (length / n_rollers)
        cyl(stage, f"{root_path}/Roller_{i + 1}",
            (x, y_center, z_top - belt_thickness - 0.05),
            0.07, width + 0.08, "Y", mats["conveyor_roller"])
    leg_w = 0.10
    leg_h = z_top - belt_thickness - 0.1
    n_legs = max(2, int(length / 2.5))
    for i in range(n_legs):
        x = x_start + (i + 0.5) * (length / n_legs)
        for sign in (-1, +1):
            cube(stage, f"{root_path}/Leg_{i + 1}_{'P' if sign > 0 else 'N'}",
                 (x, y_center + sign * (width / 2 - leg_w / 2), leg_h / 2),
                 (leg_w, leg_w, leg_h), mats[frame_mat_key])


def build_conveyor_Y(stage, root_path, y_start, y_end, x_center, z_top, width, mats,
                     frame_mat_key="conveyor_frame", belt_mat_key="conveyor_belt"):
    UsdGeom.Scope.Define(stage, root_path)
    length = y_end - y_start
    if length <= 0:
        return
    center_y = (y_start + y_end) / 2
    belt_thickness = 0.06
    cube(stage, f"{root_path}/Belt",
         (x_center, center_y, z_top - belt_thickness / 2),
         (width, length, belt_thickness), mats[belt_mat_key])
    rail_h = 0.18
    rail_w = 0.05
    cube(stage, f"{root_path}/Rail_X_neg",
         (x_center - width / 2 - rail_w / 2, center_y,
          z_top + rail_h / 4 - belt_thickness / 2),
         (rail_w, length, rail_h + belt_thickness), mats[frame_mat_key])
    cube(stage, f"{root_path}/Rail_X_pos",
         (x_center + width / 2 + rail_w / 2, center_y,
          z_top + rail_h / 4 - belt_thickness / 2),
         (rail_w, length, rail_h + belt_thickness), mats[frame_mat_key])
    n_rollers = max(2, int(length / 0.8))
    for i in range(n_rollers):
        y = y_start + (i + 0.5) * (length / n_rollers)
        cyl(stage, f"{root_path}/Roller_{i + 1}",
            (x_center, y, z_top - belt_thickness - 0.05),
            0.07, width + 0.08, "X", mats["conveyor_roller"])
    leg_w = 0.10
    leg_h = z_top - belt_thickness - 0.1
    n_legs = max(2, int(length / 2.5))
    for i in range(n_legs):
        y = y_start + (i + 0.5) * (length / n_legs)
        for sign in (-1, +1):
            cube(stage, f"{root_path}/Leg_{i + 1}_{'P' if sign > 0 else 'N'}",
                 (x_center + sign * (width / 2 - leg_w / 2), y, leg_h / 2),
                 (leg_w, leg_w, leg_h), mats[frame_mat_key])


# ============================================================================
# Truck
# ============================================================================
def build_truck(stage, root_path, trailer_rear_x, y_center, mats):
    UsdGeom.Scope.Define(stage, root_path)
    trailer_len = 5.0
    trailer_w = 2.4
    trailer_h = 2.6
    trailer_cx = trailer_rear_x - trailer_len / 2
    trailer_cz = 0.95 + trailer_h / 2
    cube(stage, f"{root_path}/Trailer", (trailer_cx, y_center, trailer_cz),
         (trailer_len, trailer_w, trailer_h), mats["truck_trailer"])
    cube(stage, f"{root_path}/TrailerDoor_Mid",
         (trailer_rear_x + 0.005, y_center, trailer_cz),
         (0.01, trailer_w * 0.92, 0.05), mats["truck_wheel"])
    cube(stage, f"{root_path}/TrailerDoor_Vert",
         (trailer_rear_x + 0.005, y_center, trailer_cz),
         (0.01, 0.05, trailer_h * 0.88), mats["truck_wheel"])
    cab_len = 2.0
    cab_w = 2.2
    cab_h = 2.2
    cab_cx = trailer_cx - trailer_len / 2 - cab_len / 2
    cab_cz = 0.95 + cab_h / 2
    cube(stage, f"{root_path}/Cab", (cab_cx, y_center, cab_cz),
         (cab_len, cab_w, cab_h), mats["truck_cab"])
    cube(stage, f"{root_path}/Cab_Windshield",
         (cab_cx - cab_len / 2 - 0.01, y_center, cab_cz + cab_h * 0.18),
         (0.02, cab_w * 0.85, cab_h * 0.45), mats["truck_window"])
    cube(stage, f"{root_path}/Cab_Hood",
         (cab_cx - cab_len / 2 - 0.35, y_center, 0.95 + 0.60),
         (0.7, cab_w * 0.85, 1.2), mats["truck_cab"])
    # 4 wheels: 1 trailer rear axle + 1 cab axle (under the cab)
    wheel_r = 0.50
    wheel_w = 0.38
    wheel_y = trailer_w / 2 + wheel_w / 2 - 0.08
    wheel_z = wheel_r
    for sign in (-1, +1):
        cyl(stage, f"{root_path}/Wheel_T_{'P' if sign > 0 else 'N'}",
            (trailer_cx + trailer_len * 0.32, y_center + sign * wheel_y, wheel_z),
            wheel_r, wheel_w, "Y", mats["truck_wheel"])
    for sign in (-1, +1):
        cyl(stage, f"{root_path}/Wheel_C_{'P' if sign > 0 else 'N'}",
            (cab_cx, y_center + sign * wheel_y, wheel_z),
            wheel_r, wheel_w, "Y", mats["truck_wheel"])


# ============================================================================
# Pipeline stations
# ============================================================================
def _station_canopy(stage, root, cx, cy, cz, sx, sy, sz, frame_mat, pad_mat):
    UsdGeom.Scope.Define(stage, f"{root}/Frame")
    pw = 0.10
    for sxs, sys_, lbl in [(-1, -1, "SW"), (-1, +1, "NW"),
                           (+1, -1, "SE"), (+1, +1, "NE")]:
        x = cx + sxs * (sx / 2 - pw / 2)
        y = cy + sys_ * (sy / 2 - pw / 2)
        cube(stage, f"{root}/Frame/Post_{lbl}",
             (x, y, cz + sz / 2), (pw, pw, sz), frame_mat)
    bw = 0.10
    beam_z = cz + sz - bw / 2
    cube(stage, f"{root}/Frame/Beam_Front", (cx, cy - sy / 2 + bw / 2, beam_z),
         (sx, bw, bw), frame_mat)
    cube(stage, f"{root}/Frame/Beam_Back", (cx, cy + sy / 2 - bw / 2, beam_z),
         (sx, bw, bw), frame_mat)
    cube(stage, f"{root}/Frame/Beam_Cross", (cx, cy, beam_z),
         (bw, sy, bw), frame_mat)
    cube(stage, f"{root}/Pad", (cx, cy, 0.05), (sx, sy, 0.05), pad_mat)


def build_station_probing(stage, root, cx, mats):
    cy, cz = 0.0, 0.1
    sx, sy, sz = 1.8, 3.0, 3.0
    _station_canopy(stage, root, cx, cy, cz, sx, sy, sz,
                    mats["steel_frame"], mats["concrete"])
    base_h = 0.30
    cube(stage, f"{root}/Arm/Base",
         (cx, cy + sy * 0.32, cz + base_h / 2),
         (0.40, 0.40, base_h), mats["machine_probing"])
    cyl(stage, f"{root}/Arm/Shaft",
        (cx, cy + sy * 0.32, cz + base_h + 0.70),
        0.10, 1.40, "Z", mats["machine_probing"])
    cube(stage, f"{root}/Arm/Horizontal",
         (cx, cy + sy * 0.05, cz + base_h + 1.30),
         (0.10, sy * 0.55, 0.10), mats["machine_probing"])
    cube(stage, f"{root}/Arm/ScannerHead",
         (cx, cy - sy * 0.10, cz + base_h + 1.10),
         (0.30, 0.30, 0.20), mats["scanner_red"])
    cyl(stage, f"{root}/Arm/ScannerBeam",
        (cx, cy - sy * 0.10, cz + base_h + 0.60),
        0.10, 0.80, "Z", mats["scanner_beam"])
    for label, x_off in [("JSON", -0.50), ("CSV", 0.0), ("TSV", 0.50)]:
        cube(stage, f"{root}/FormatIcons/{label}",
             (cx + x_off, cy + sy * 0.45, cz + sz + 0.40),
             (0.35, 0.05, 0.22), mats["machine_probing"])


def build_station_architect(stage, root, cx, mats):
    cy, cz = 0.0, 0.1
    sx, sy, sz = 1.8, 3.0, 3.0
    _station_canopy(stage, root, cx, cy, cz, sx, sy, sz,
                    mats["steel_frame"], mats["concrete"])
    cube(stage, f"{root}/Desk", (cx, cy + sy * 0.30, cz + 0.45),
         (1.2, 0.6, 0.10), mats["machine_architect"])
    cube(stage, f"{root}/DeskLeg_L", (cx - 0.50, cy + sy * 0.30, cz + 0.20),
         (0.08, 0.6, 0.40), mats["steel_frame"])
    cube(stage, f"{root}/DeskLeg_R", (cx + 0.50, cy + sy * 0.30, cz + 0.20),
         (0.08, 0.6, 0.40), mats["steel_frame"])
    cube(stage, f"{root}/Monitor", (cx, cy + sy * 0.36, cz + 1.10),
         (0.90, 0.05, 1.10), mats["monitor_screen"])
    schema_z = cz + 1.50
    tree = [
        (cx, cy - 0.30, schema_z, 0.22),
        (cx - 0.30, cy - 0.30, schema_z - 0.35, 0.16),
        (cx, cy - 0.30, schema_z - 0.35, 0.16),
        (cx + 0.30, cy - 0.30, schema_z - 0.35, 0.16),
        (cx - 0.30, cy - 0.30, schema_z - 0.70, 0.12),
        (cx + 0.30, cy - 0.30, schema_z - 0.70, 0.12),
    ]
    for i, (x, y, z, s) in enumerate(tree):
        cube(stage, f"{root}/SchemaTree/Node_{i + 1}", (x, y, z),
             (s, s, s), mats["machine_architect"])


def build_station_iceberg(stage, root, cx, mats):
    cy, cz = 0.0, 0.1
    sx, sy, sz = 1.8, 3.0, 3.0
    _station_canopy(stage, root, cx, cy, cz, sx, sy, sz,
                    mats["steel_frame"], mats["concrete"])
    arch_top_z = cz + 1.30
    arch_w = 1.40
    arch_t = 0.12
    cube(stage, f"{root}/Arch/PostL", (cx, cy - 0.50, cz + arch_top_z / 2),
         (0.12, 0.10, arch_top_z), mats["machine_iceberg"])
    cube(stage, f"{root}/Arch/PostR", (cx, cy + 0.50, cz + arch_top_z / 2),
         (0.12, 0.10, arch_top_z), mats["machine_iceberg"])
    cube(stage, f"{root}/Arch/Top", (cx, cy, cz + arch_top_z),
         (0.20, arch_w, arch_t), mats["machine_iceberg"])
    for i, y_off in enumerate([-0.40, -0.20, 0.0, 0.20, 0.40]):
        cyl(stage, f"{root}/Arch/Nozzle_{i + 1}",
            (cx, cy + y_off, cz + arch_top_z - 0.18),
            0.04, 0.10, "Z", mats["machine_iceberg"])
    sphere(stage, f"{root}/SnowflakeEmblem",
           (cx, cy, cz + sz + 0.25), 0.20, mats["machine_iceberg"])
    cyl(stage, f"{root}/SparkEmber",
        (cx + 0.45, cy, cz + sz + 0.25), 0.10, 0.10, "Z", mats["conveyor_frame"])


def build_station_milvus(stage, root, cx, mats):
    cy, cz = 0.0, 0.1
    sx, sy, sz = 1.8, 3.0, 3.0
    _station_canopy(stage, root, cx, cy, cz, sx, sy, sz,
                    mats["steel_frame"], mats["concrete"])
    cube(stage, f"{root}/Machine/Column", (cx, cy + sy * 0.32, cz + 1.10),
         (0.30, 0.30, 2.20), mats["machine_milvus"])
    cube(stage, f"{root}/Machine/Arm", (cx, cy + sy * 0.10, cz + 0.85),
         (0.20, sy * 0.45, 0.20), mats["machine_milvus"])
    cube(stage, f"{root}/Machine/StampHead", (cx, cy - sy * 0.08, cz + 0.85),
         (0.30, 0.10, 0.40), mats["milvus_label"])
    cube(stage, f"{root}/HologramLabel",
         (cx, cy - sy * 0.32, cz + 1.20),
         (0.50, 0.04, 0.30), mats["milvus_label"])


def build_station_redis(stage, root, cx, mats):
    cy, cz = 0.0, 0.1
    sx, sy, sz = 1.8, 3.0, 3.0
    _station_canopy(stage, root, cx, cy, cz, sx, sy, sz,
                    mats["steel_frame"], mats["concrete"])
    cube(stage, f"{root}/Dispenser/Body", (cx, cy, cz + sz - 0.40),
         (0.50, 0.50, 0.40), mats["machine_redis"])
    cube(stage, f"{root}/Dispenser/Chute", (cx, cy, cz + sz - 0.70),
         (0.30, 0.30, 0.20), mats["machine_redis"])
    cube(stage, f"{root}/Dispenser/CardSample", (cx, cy, cz + 1.30),
         (0.40, 0.30, 0.03), mats["redis_card"])
    cyl(stage, f"{root}/Indicator",
        (cx + sx * 0.42, cy + sy * 0.30, cz + sz - 0.30),
        0.08, 0.12, "Z", mats["led_red"])


# ============================================================================
# Audit Gate
# ============================================================================
def build_audit_gate(stage, root_path, cx, mats):
    UsdGeom.Scope.Define(stage, root_path)
    cy, cz = 0.0, 0.1
    sx, sy, sz = 2.5, 5.0, 3.6
    _station_canopy(stage, root_path, cx, cy, cz, sx, sy, sz,
                    mats["steel_frame"], mats["concrete"])
    cube(stage, f"{root_path}/Wall_N",
         (cx, cy + sy / 2 - 0.05, cz + sz / 2),
         (sx, 0.05, sz), mats["zone_color_35"])
    cube(stage, f"{root_path}/Wall_S",
         (cx, cy - sy / 2 + 0.05, cz + sz / 2),
         (sx, 0.05, sz), mats["zone_color_35"])
    cube(stage, f"{root_path}/Arch_Top", (cx, cy, cz + sz - 0.30),
         (sx * 0.6, sy * 0.05, 0.30), mats["zone_color_35"])
    cube(stage, f"{root_path}/Arch_LeftPost",
         (cx, cy - sy * 0.025, cz + sz / 2),
         (sx * 0.6, 0.10, sz), mats["zone_color_35"])
    sphere(stage, f"{root_path}/PassLight",
           (cx - 0.5, cy + sy / 2 - 0.20, cz + sz + 0.25),
           0.22, mats["audit_pass"])
    cube(stage, f"{root_path}/PassLabel",
         (cx - 0.5, cy + sy / 2 - 0.20, cz + sz - 0.15),
         (0.6, 0.05, 0.20), mats["audit_pass"])
    sphere(stage, f"{root_path}/FailLight",
           (cx + 0.5, cy + sy / 2 - 0.20, cz + sz + 0.25),
           0.22, mats["audit_fail"])
    cube(stage, f"{root_path}/FailLabel",
         (cx + 0.5, cy + sy / 2 - 0.20, cz + sz - 0.15),
         (0.6, 0.05, 0.20), mats["audit_fail"])
    cube(stage, f"{root_path}/RejectChute",
         (cx + 1.4, cy - sy * 0.30, 0.50),
         (0.6, 1.4, 0.06), mats["audit_fail"])
    cube(stage, f"{root_path}/RejectBin",
         (cx + 1.4, cy - sy * 0.55, 0.50),
         (1.0, 0.8, 1.0), mats["audit_fail"])


# ============================================================================
# Vehicles
# ============================================================================
def _generic_van(stage, root_path, anchor_x, y_center, body_mat, accent_mat,
                  cab_mat, mats, body_len=3.6, body_w=2.0, body_h=2.0,
                  facing="east"):
    """Delivery van.
    facing='east': cab on +X side, rear (open doors) on -X side (anchor_x is the rear).
    facing='west': cab on -X side, rear on +X side (anchor_x is the rear at +X).
    """
    UsdGeom.Scope.Define(stage, root_path)
    sign_x = +1 if facing == "east" else -1
    body_cx = anchor_x + sign_x * body_len / 2
    body_cz = 0.85 + body_h / 2
    cube(stage, f"{root_path}/Body", (body_cx, y_center, body_cz),
         (body_len, body_w, body_h), body_mat)
    cab_len = 1.4
    cab_h = 1.6
    cab_cx = body_cx + sign_x * (body_len / 2 + cab_len / 2)
    cab_cz = 0.85 + cab_h / 2
    cube(stage, f"{root_path}/Cab", (cab_cx, y_center, cab_cz),
         (cab_len, body_w * 0.95, cab_h), cab_mat)
    # Windshield faces outward (away from facility)
    cube(stage, f"{root_path}/Windshield",
         (cab_cx + sign_x * (cab_len / 2 + 0.01), y_center, cab_cz + cab_h * 0.15),
         (0.02, body_w * 0.8, cab_h * 0.45), mats["truck_window"])
    # Rear doors at -sign_x end of body (facing the table)
    rear_x = body_cx - sign_x * body_len / 2
    cube(stage, f"{root_path}/RearDoorMid",
         (rear_x - sign_x * 0.01, y_center, body_cz),
         (0.02, body_w * 0.92, 0.05), mats["truck_wheel"])
    cube(stage, f"{root_path}/RearDoorVert",
         (rear_x - sign_x * 0.01, y_center, body_cz),
         (0.02, 0.05, body_h * 0.88), mats["truck_wheel"])
    cube(stage, f"{root_path}/AccentStripe",
         (body_cx, y_center + body_w / 2 + 0.012, body_cz),
         (body_len * 0.9, 0.025, 0.18), accent_mat)
    cube(stage, f"{root_path}/LogoDecal",
         (body_cx, y_center + body_w / 2 + 0.024, body_cz + body_h * 0.25),
         (body_len * 0.4, 0.025, body_h * 0.3), accent_mat)
    # 4 wheels: 1 body axle (rear) + 1 cab axle (front)
    wheel_r = 0.42
    wheel_w = 0.32
    wheel_y = body_w / 2 + wheel_w / 2 - 0.07
    wheel_z = wheel_r
    for sign in (-1, +1):
        cyl(stage, f"{root_path}/Wheel_B_{'P' if sign > 0 else 'N'}",
            (body_cx - sign_x * body_len * 0.28, y_center + sign * wheel_y, wheel_z),
            wheel_r, wheel_w, "Y", mats["truck_wheel"])
    for sign in (-1, +1):
        cyl(stage, f"{root_path}/Wheel_C_{'P' if sign > 0 else 'N'}",
            (cab_cx, y_center + sign * wheel_y, wheel_z),
            wheel_r, wheel_w, "Y", mats["truck_wheel"])


def build_ai_truck(stage, root_path, anchor_x, y_center, mats):
    _generic_van(stage, root_path, anchor_x, y_center,
                 mats["ai_truck"], mats["ai_truck_accent"], mats["ai_truck"], mats,
                 body_len=3.8, body_w=2.2, body_h=2.2)


def build_hpc_van(stage, root_path, anchor_x, y_center, mats):
    _generic_van(stage, root_path, anchor_x, y_center,
                 mats["hpc_van"], mats["hpc_van_accent"], mats["hpc_van_accent"], mats,
                 body_len=3.4, body_w=2.0, body_h=2.0)


def build_hpda_van(stage, root_path, anchor_x, y_center, mats):
    _generic_van(stage, root_path, anchor_x, y_center,
                 mats["hpda_van"], mats["hpda_van_accent"], mats["hpda_van"], mats,
                 body_len=3.6, body_w=2.0, body_h=2.0)


# ============================================================================
# Dock loading table — receives boxes from belts and hands them to truck
# ============================================================================
def build_dock_table(stage, root_path, cx, cy, mats, with_boxes=True):
    """Wide flat loading table. LH belt arrives at -Y edge, SC belt at +Y edge,
    truck parked at +X (open rear) takes boxes from the table."""
    UsdGeom.Scope.Define(stage, root_path)
    table_w = 2.4   # X
    table_d = 3.2   # Y
    table_top_z = 0.78
    leg_h = table_top_z - 0.05
    floor_z = 0.10
    leg_w = 0.10
    for sxs, sys_, lbl in [(-1, -1, "SW"), (-1, +1, "NW"),
                           (+1, -1, "SE"), (+1, +1, "NE")]:
        cube(stage, f"{root_path}/Leg_{lbl}",
             (cx + sxs * (table_w / 2 - leg_w / 2),
              cy + sys_ * (table_d / 2 - leg_w / 2),
              floor_z + leg_h / 2),
             (leg_w, leg_w, leg_h), mats["table_leg"])
    cube(stage, f"{root_path}/Top", (cx, cy, floor_z + table_top_z),
         (table_w, table_d, 0.08), mats["table_top"])
    # Decorative belt-side rails on N and S edges (where belts arrive)
    cube(stage, f"{root_path}/RailS",
         (cx, cy - table_d / 2 + 0.04, floor_z + table_top_z + 0.06),
         (table_w * 0.95, 0.06, 0.08), mats["conveyor_cold"])
    cube(stage, f"{root_path}/RailN",
         (cx, cy + table_d / 2 - 0.04, floor_z + table_top_z + 0.06),
         (table_w * 0.95, 0.06, 0.08), mats["conveyor_hot"])
    if with_boxes:
        # 2 iceberg boxes sitting on the table, waiting to be loaded
        make_iceberg_box(stage, f"{root_path}/Box_Cold",
                         (cx - 0.5, cy - 0.7, floor_z + table_top_z + 0.05 + 0.20),
                         (0.50, 0.36, 0.40), mats, led="green")
        make_iceberg_box(stage, f"{root_path}/Box_Hot",
                         (cx + 0.5, cy + 0.7, floor_z + table_top_z + 0.05 + 0.20),
                         (0.50, 0.36, 0.40), mats, led="yellow")


# ============================================================================
# Delivery dock canopy (without the conveyor-fed pad — now upstream of truck)
# ============================================================================
def build_delivery_dock(stage, root_path, x_dock, y_dock, mats, label_color_mat):
    UsdGeom.Scope.Define(stage, root_path)
    cube(stage, f"{root_path}/Pad",
         (x_dock, y_dock, 0.05), (3.2, 3.2, 0.10), mats["concrete"])
    for sxs, sys_, lbl in [(-1, -1, "SW"), (-1, +1, "NW"),
                           (+1, -1, "SE"), (+1, +1, "NE")]:
        cube(stage, f"{root_path}/Post_{lbl}",
             (x_dock + sxs * 1.4, y_dock + sys_ * 1.4, 1.6),
             (0.12, 0.12, 3.2), mats["steel_frame"])
    cube(stage, f"{root_path}/Roof",
         (x_dock, y_dock, 3.18), (3.0, 3.0, 0.10), label_color_mat)
    cube(stage, f"{root_path}/Interface",
         (x_dock, y_dock, 0.95), (1.0, 1.0, 1.8), mats["workload"])
    cube(stage, f"{root_path}/InterfaceScreen",
         (x_dock - 0.55, y_dock, 1.45), (0.05, 0.6, 0.5), mats["monitor_screen"])


# ============================================================================
# Search Counter
# ============================================================================
def build_search_counter(stage, root_path, cx, cy, mats):
    UsdGeom.Scope.Define(stage, root_path)
    cube(stage, f"{root_path}/Desk", (cx, cy, 0.55),
         (3.2, 1.0, 1.1), mats["operator"])
    cube(stage, f"{root_path}/DeskTop", (cx, cy, 1.12),
         (3.4, 1.1, 0.06), mats["white_panel"])
    cube(stage, f"{root_path}/Terminal", (cx, cy + 0.20, 1.55),
         (1.0, 0.05, 0.65), mats["monitor_screen"])
    panel_z = 2.40
    cube(stage, f"{root_path}/IndicatorPanel/Backboard",
         (cx, cy + 0.25, panel_z), (2.6, 0.06, 0.55), mats["steel_frame"])
    for label, color_key, x_off in [
        ("Milvus", "indicator_milvus", -0.9),
        ("LLM",    "indicator_llm",     0.0),
        ("Redis",  "indicator_redis",   0.9),
    ]:
        cyl(stage, f"{root_path}/IndicatorPanel/Light_{label}",
            (cx + x_off, cy + 0.27, panel_z),
            0.20, 0.14, "Y", mats[color_key])
    cube(stage, f"{root_path}/IndicatorPanel/Pole_L",
         (cx - 1.30, cy + 0.25, 1.85), (0.08, 0.08, 1.30), mats["steel_frame"])
    cube(stage, f"{root_path}/IndicatorPanel/Pole_R",
         (cx + 1.30, cy + 0.25, 1.85), (0.08, 0.08, 1.30), mats["steel_frame"])


# ============================================================================
# Catalog Office
# ============================================================================
def build_catalog_office(stage, root_path, center, size, mats):
    cx, cy, cz = center
    sx, sy, sz = size
    cube(stage, f"{root_path}/Floor", (cx, cy, cz), (sx, sy, 0.15), mats["concrete"])
    build_glass_office(stage, root_path, (cx, cy, cz + 0.05),
                       (sx, sy, sz), mats["glass_office"], mats["steel_frame"])
    UsdGeom.Scope.Define(stage, f"{root_path}/Interior")
    for label, x_off, color_key in [
        ("Lineage",    -1.5, "monitor_screen"),
        ("RBAC",        0.0, "indicator_milvus"),
        ("QualitySLO",  1.5, "led_green"),
    ]:
        cube(stage, f"{root_path}/Interior/Monitor_{label}",
             (cx + x_off, cy + sy * 0.40, cz + 1.50),
             (1.1, 0.06, 0.75), mats[color_key])
    cube(stage, f"{root_path}/Interior/Desk",
         (cx, cy - sy * 0.10, cz + 0.45),
         (sx * 0.7, 0.7, 0.10), mats["machine_architect"])
    cube(stage, f"{root_path}/Interior/Chair",
         (cx, cy - sy * 0.30, cz + 0.50),
         (0.55, 0.55, 1.0), mats["operator"])


# ============================================================================
# Control Tower
# ============================================================================
def build_control_tower(stage, root_path, cx, cy, mats):
    UsdGeom.Scope.Define(stage, root_path)
    cube(stage, f"{root_path}/Base", (cx, cy, 0.55), (3.2, 3.2, 1.1), mats["concrete"])
    shaft_h = 9.0
    cube(stage, f"{root_path}/Shaft", (cx, cy, 1.1 + shaft_h / 2),
         (1.0, 1.0, shaft_h), mats["steel_frame"])
    deck_z = 1.1 + shaft_h + 1.0
    cube(stage, f"{root_path}/DeckFloor", (cx, cy, deck_z - 1.0),
         (3.8, 3.8, 0.15), mats["concrete"])
    build_glass_office(stage, f"{root_path}/Deck",
                       (cx, cy, deck_z - 0.95),
                       (3.8, 3.8, 2.0), mats["glass_tower"], mats["steel_frame"])
    cyl(stage, f"{root_path}/Antenna",
        (cx, cy, deck_z + 1.8), 0.06, 1.6, "Z", mats["steel_frame"])
    sphere(stage, f"{root_path}/AntennaTip",
           (cx, cy, deck_z + 2.7), 0.14, mats["led_red"])
    cube(stage, f"{root_path}/OperatorChair",
         (cx, cy - 0.5, deck_z - 0.55), (0.5, 0.5, 1.0), mats["operator"])
    cube(stage, f"{root_path}/OperatorDesk",
         (cx, cy + 0.5, deck_z - 0.65), (2.0, 0.6, 0.10), mats["machine_explain"])


# ============================================================================
# Lobby (entry gate + reception)
# ============================================================================
def build_lobby_entrance(stage, root_path, cx, cy, mats):
    UsdGeom.Scope.Define(stage, root_path)
    cube(stage, f"{root_path}/Plaza", (cx, cy, 0.05),
         (7.0, 7.0, 0.10), mats["white_panel"])
    # Reception desk + monitor (gate removed per design update)
    cube(stage, f"{root_path}/Reception/Desk",
         (cx, cy + 2.2, 0.55), (3.0, 0.8, 1.1), mats["operator"])
    cube(stage, f"{root_path}/Reception/Monitor",
         (cx, cy + 2.4, 1.55), (1.0, 0.05, 0.6), mats["monitor_screen"])


# ============================================================================
# Mannequin
# ============================================================================
def build_mannequin(stage, root_path, pos, role, mats):
    role_colors = {
        "admin": "role_admin",
        "operator": "role_operator",
        "researcher": "role_researcher",
        "viewer": "role_viewer",
        "service": "role_service",
    }
    body_mat = mats[role_colors[role]]
    UsdGeom.Scope.Define(stage, root_path)
    x, y, z = pos
    cube(stage, f"{root_path}/Torso", (x, y, z + 0.95),
         (0.40, 0.28, 0.95), body_mat)
    cube(stage, f"{root_path}/Leg_L", (x - 0.10, y, z + 0.35),
         (0.16, 0.20, 0.70), mats["role_viewer"] if role != "service" else body_mat)
    cube(stage, f"{root_path}/Leg_R", (x + 0.10, y, z + 0.35),
         (0.16, 0.20, 0.70), mats["role_viewer"] if role != "service" else body_mat)
    cube(stage, f"{root_path}/Arm_L", (x - 0.30, y, z + 1.05),
         (0.13, 0.20, 0.75), body_mat)
    cube(stage, f"{root_path}/Arm_R", (x + 0.30, y, z + 1.05),
         (0.13, 0.20, 0.75), body_mat)
    sphere(stage, f"{root_path}/Head", (x, y, z + 1.70), 0.18,
           mats["role_service"] if role == "service" else mats["skin_tone"])
    cube(stage, f"{root_path}/Badge",
         (x, y, z + 2.10), (0.40, 0.04, 0.22), body_mat)


# ============================================================================
# MAIN
# ============================================================================
def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    stage = Usd.Stage.CreateNew(str(OUT))
    stage.SetStartTimeCode(0)
    stage.SetEndTimeCode(150)
    stage.SetTimeCodesPerSecond(24)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    UsdGeom.SetStageMetersPerUnit(stage, 1.0)

    UsdGeom.Xform.Define(stage, "/World")
    for scope in [
        "/World/Materials", "/World/Environment", "/World/ZonePads",
        "/World/Lobby", "/World/TruckYard", "/World/LoadingDock",
        "/World/Lake", "/World/AccumulationPipeline",
        "/World/Pipeline", "/World/Metadata", "/World/AuditGate",
        "/World/Lakehouse", "/World/Showcase",
        "/World/CatalogOffice", "/World/SearchCounter",
        "/World/Delivery", "/World/DeliveryYard", "/World/WorkloadInterfaces",
        "/World/ControlTower", "/World/Operations",
        "/World/Datasets", "/World/Avatars",
    ]:
        UsdGeom.Scope.Define(stage, scope)

    mats = {k: create_mat(stage, k, c, o) for k, (c, o) in COLORS.items()}

    # ===== Environment =====
    cube(stage, "/World/Environment/Floor", (25, 8, -0.05),
         (110, 48, 0.10), mats["floor"])
    sun = UsdLux.DistantLight.Define(stage, "/World/Environment/SunLight")
    sun.CreateIntensityAttr(3200.0)
    sun.CreateAngleAttr(0.6)
    UsdGeom.XformCommonAPI(sun).SetRotate(Gf.Vec3f(-50, 30, 0))
    dome = UsdLux.DomeLight.Define(stage, "/World/Environment/SkyDome")
    dome.CreateIntensityAttr(1100.0)

    # -------------------------------------------------------------------
    # v5 Layout: warehouses ~3x area (17x12x6, down from v4's 20x14x7).
    #            Trucks parked east of tables; truck rear (open) faces west toward
    #            tables. Each table receives one LH belt (south side) + one SC
    #            belt (north side). Lobby+Search Counter sits in the gap between
    #            LH and SC on the middle Y line.
    #
    #   Control Tower:        (-22, -13)        (stays)
    #   Truck Yard:           (-18,   0)
    #   Raw Bucket:           ( -4,   0)  17 x 12 x 6
    #   Pipeline stations:    X = 7, 10, 13, 16, 19
    #   Lakehouse:            (+29,   0)  17 x 12 x 6   (Y range -6 .. +6)
    #   Showcase:             (+29, +15)  17 x 12 x 6   (Y range +9 .. +21)
    #   Promotion belt:       X=+29, Y = +6 -> +9
    #   Lobby + Search Counter plaza: (+49, +7.5)   middle Y line
    #   Tables:               (+58, -5), (+58, 0), (+58, +5)
    #   Trucks (facing east): rear at X=+59.5, cab to +X side
    # -------------------------------------------------------------------

    # ===== Zone floor pads (colored identification, no signposts) =====
    zone_pad(stage, "/World/ZonePads/Tower",       (-22,  -13), (6,  6),  mats["zone_color_9"])
    zone_pad(stage, "/World/ZonePads/TruckYard",   (-22,    0), (16, 8),  mats["zone_color_1"])
    zone_pad(stage, "/World/ZonePads/RawBucket",   ( -4,    0), (19, 14), mats["metal_bronze"])
    zone_pad(stage, "/World/ZonePads/Pipeline",    (+13,    0), (16, 7),  mats["metal_silver"])
    zone_pad(stage, "/World/ZonePads/Lakehouse",   (+29,    0), (19, 14), mats["metal_silver"])
    zone_pad(stage, "/World/ZonePads/Showcase",    (+29,  +22), (19, 14), mats["metal_gold"])
    zone_pad(stage, "/World/ZonePads/LobbySearch", (+44, +10), (10, 11), mats["zone_color_0"])
    zone_pad(stage, "/World/ZonePads/Delivery",    (+59,  +10), (22, 14), mats["zone_color_8"])

    # ===== Zone 9: Control Tower (stays at south-west) =====
    build_control_tower(stage, "/World/ControlTower", cx=-22.0, cy=-13.0, mats=mats)
    cube(stage, "/World/Operations/OperatorDesk", (-22.0, -12.5, 11.5),
         (0.10, 0.10, 0.10), mats["operator"],
         name="System Operator Desk (Control Tower)",
         entity_id="operator.control", entity_type="operator",
         stage_name="monitoring")

    # ===== Zone 1: Truck Yard (truck pushed further west, longer inbound belt) =====
    cube(stage, "/World/TruckYard/Asphalt", (-22.0, 0, -0.02),
         (14.0, 8.0, 0.05), mats["asphalt"])
    for i, y in enumerate([-3.5, 3.5]):
        cube(stage, f"/World/TruckYard/Stripe_{i + 1}",
             (-22.0, y, 0.025), (14.0, 0.15, 0.01), mats["zone_color_1"])
    build_truck(stage, "/World/LoadingDock/Truck",
                trailer_rear_x=-18.0, y_center=0.0, mats=mats)

    # Inbound conveyor: long stretch from truck rear (-17.9) to Raw west wall (-12.5)
    # BRONZE frame — this belt feeds the Raw / Bronze stage.
    build_conveyor(stage, "/World/LoadingDock/InboundConveyor",
                   x_start=-17.9, x_end=-12.3, y_center=0.0,
                   z_top=0.7, width=1.0, mats=mats,
                   frame_mat_key="metal_bronze")

    # ===== Zone 2: Raw Bucket Warehouse (17 x 12 x 6) =====
    raw_cx, raw_cy, raw_cz = -4.0, 0.0, 0.10
    raw_sx, raw_sy, raw_sz = 17.0, 12.0, 6.0
    cube(stage, "/World/Lake/BronzeLake",
         (raw_cx, raw_cy, raw_cz),
         (raw_sx, raw_sy, 0.18), mats["concrete"],
         name="Bronze Lake", entity_id="lake.bronze",
         entity_type="storage_zone", stage_name="accumulation")
    build_warehouse(stage, "/World/Lake",
                    center=(raw_cx, raw_cy, raw_cz + 0.10),
                    size=(raw_sx, raw_sy, raw_sz),
                    wall_mat=mats["glass_lake"], frame_mat=mats["steel_frame"],
                    left_gap=(0.0, 1.4, 1.1), right_gap=(0.0, 1.4, 1.1))
    # Brown raw boxes piled inside (Data Swamp visualization)
    UsdGeom.Scope.Define(stage, "/World/Lake/Contents")
    raw_layout = [
        # ----- South wall row (Y=-5), 3-tall stacks at west, dense west-to-east -----
        (-11.5, -5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-11.5, -5.0, 1.15, 0.7, 0.7, 0.7, True),
        (-11.5, -5.0, 1.90, 0.6, 0.6, 0.6, False),
        (-10.7, -5.0, 0.40, 0.7, 0.7, 0.7, True),
        (-10.7, -5.0, 1.15, 0.6, 0.6, 0.6, False),
        (-9.9,  -5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-9.9,  -5.0, 1.15, 0.6, 0.6, 0.6, True),
        (-9.1,  -5.0, 0.40, 0.7, 0.7, 0.7, True),
        (-9.1,  -5.0, 1.15, 0.6, 0.6, 0.6, False),
        (-8.3,  -5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-7.5,  -5.0, 0.40, 0.7, 0.7, 0.7, True),
        (-6.7,  -5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-5.9,  -5.0, 0.40, 0.7, 0.7, 0.7, True),
        (-5.1,  -5.0, 0.40, 0.6, 0.6, 0.6, False),
        (-4.3,  -5.0, 0.40, 0.6, 0.6, 0.6, True),
        (-3.5,  -5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-2.7,  -5.0, 0.40, 0.7, 0.7, 0.7, True),
        (-1.9,  -5.0, 0.40, 0.6, 0.6, 0.6, False),
        (-1.1,  -5.0, 0.40, 0.6, 0.6, 0.6, True),
        # ----- North wall row (Y=+5) -----
        (-11.5, 5.0, 0.40, 0.7, 0.7, 0.7, True),
        (-11.5, 5.0, 1.15, 0.6, 0.6, 0.6, False),
        (-10.7, 5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-10.7, 5.0, 1.15, 0.7, 0.7, 0.7, True),
        (-9.9,  5.0, 0.40, 0.6, 0.6, 0.6, True),
        (-9.1,  5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-9.1,  5.0, 1.15, 0.6, 0.6, 0.6, True),
        (-8.3,  5.0, 0.40, 0.7, 0.7, 0.7, True),
        (-7.5,  5.0, 0.40, 0.6, 0.6, 0.6, False),
        (-6.7,  5.0, 0.40, 0.7, 0.7, 0.7, True),
        (-5.9,  5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-5.1,  5.0, 0.40, 0.6, 0.6, 0.6, True),
        (-4.3,  5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-3.5,  5.0, 0.40, 0.6, 0.6, 0.6, True),
        (-2.7,  5.0, 0.40, 0.7, 0.7, 0.7, False),
        (-1.9,  5.0, 0.40, 0.6, 0.6, 0.6, True),
        # ----- Middle clusters -----
        (-10.5, -2.5, 0.40, 0.6, 0.6, 0.6, True),
        (-10.5, -2.5, 1.05, 0.6, 0.6, 0.6, False),
        (-9.5,  -2.5, 0.40, 0.7, 0.7, 0.7, False),
        (-8.5,  -2.5, 0.40, 0.6, 0.6, 0.6, True),
        (-7.5,  -2.5, 0.40, 0.7, 0.7, 0.7, True),
        (-6.5,  -2.5, 0.40, 0.6, 0.6, 0.6, False),
        (-5.5,  -2.5, 0.40, 0.6, 0.6, 0.6, True),
        (-4.5,  -2.5, 0.40, 0.7, 0.7, 0.7, False),
        (-3.5,  -2.5, 0.40, 0.6, 0.6, 0.6, True),
        (-10.5,  2.5, 0.40, 0.6, 0.6, 0.6, False),
        (-10.5,  2.5, 1.05, 0.6, 0.6, 0.6, True),
        (-9.5,   2.5, 0.40, 0.7, 0.7, 0.7, True),
        (-8.5,   2.5, 0.40, 0.6, 0.6, 0.6, False),
        (-7.5,   2.5, 0.40, 0.7, 0.7, 0.7, False),
        (-6.5,   2.5, 0.40, 0.6, 0.6, 0.6, True),
        (-5.5,   2.5, 0.40, 0.7, 0.7, 0.7, True),
        (-4.5,   2.5, 0.40, 0.6, 0.6, 0.6, False),
        (-3.5,   2.5, 0.40, 0.7, 0.7, 0.7, False),
        # ----- Central aisle scatter -----
        (-9.0,  0.0, 0.40, 0.6, 0.6, 0.6, True),
        (-7.0,  0.0, 0.40, 0.7, 0.7, 0.7, False),
        (-5.0,  0.0, 0.40, 0.6, 0.6, 0.6, True),
        (-3.0,  0.0, 0.40, 0.7, 0.7, 0.7, True),
        (-10.0, 1.2, 0.40, 0.5, 0.5, 0.5, False),
        (-8.0, -1.2, 0.40, 0.5, 0.5, 0.5, True),
        (-6.0,  1.2, 0.40, 0.5, 0.5, 0.5, False),
        (-4.0, -1.2, 0.40, 0.5, 0.5, 0.5, True),
        (-2.0,  0.5, 0.40, 0.6, 0.6, 0.6, False),
    ]
    for i, (x, y, z, sx, sy, sz, dark) in enumerate(raw_layout):
        make_raw_box(stage, f"/World/Lake/Contents/Raw_{i + 1}",
                     (x, y, z), (sx, sy, sz), mats, dark=dark)

    # No conveyor inside Raw Bucket — boxes simply rest there as storage.
    # Two parallel SAME-SIZE belts (Main + Express) start at Raw east wall
    # and run all the way through the pipeline stations to Lakehouse west.

    # ===== Zone 3: Pipeline (main + express) =====
    station_x = [7.0, 10.0, 13.0, 16.0, 19.0]
    build_station_probing(stage,  "/World/Pipeline/Station_Probing",   station_x[0], mats)
    build_station_architect(stage, "/World/Pipeline/Station_Architect", station_x[1], mats)
    build_station_iceberg(stage,  "/World/Pipeline/Station_Iceberg",   station_x[2], mats)
    build_station_milvus(stage,   "/World/Pipeline/Station_Milvus",    station_x[3], mats)
    build_station_redis(stage,    "/World/Pipeline/Station_Redis",     station_x[4], mats)

    # Main belt — starts at Raw east wall (+4.7), Y=-0.7. SILVER frame.
    build_conveyor(stage, "/World/AccumulationPipeline/InputConveyor",
                   x_start=4.7, x_end=20.4, y_center=-0.7,
                   z_top=0.7, width=1.0, mats=mats,
                   frame_mat_key="metal_silver")
    p = stage.GetPrimAtPath("/World/AccumulationPipeline/InputConveyor")
    p.CreateAttribute("trident:entity_id", Sdf.ValueTypeNames.String).Set("pipeline.accumulation")
    p.CreateAttribute("trident:entity_type", Sdf.ValueTypeNames.String).Set("pipeline")
    p.CreateAttribute("trident:stage", Sdf.ValueTypeNames.String).Set("accumulation")
    p.CreateAttribute("trident:name", Sdf.ValueTypeNames.String).Set("Pipeline Main Line (Full Mode)")
    # Express belt — SAME size as main, parallel at Y=+0.7. SILVER frame.
    build_conveyor(stage, "/World/AccumulationPipeline/ExpressLine",
                   x_start=4.7, x_end=20.4, y_center=+0.7,
                   z_top=0.7, width=1.0, mats=mats,
                   frame_mat_key="metal_silver",
                   belt_mat_key="conveyor_belt_express")
    # Replay-compat metadata station anchors
    cube(stage, "/World/Metadata/ExplainingStation",
         (station_x[3], 0.0, 0.04),
         (1.6, 3.0, 0.04), mats["concrete"],
         name="Explaining Metadata Station (Milvus)",
         entity_id="station.metadata.explaining",
         entity_type="metadata_station", stage_name="explaining")
    cube(stage, "/World/Metadata/SharingStation",
         (station_x[4], 0.0, 0.04),
         (1.6, 3.0, 0.04), mats["concrete"],
         name="Sharing Metadata Station (Redis)",
         entity_id="station.metadata.sharing",
         entity_type="metadata_station", stage_name="sharing")
    cube(stage, "/World/AccumulationPipeline/ToLakehouseConveyor",
         (22.0, 0.0, 0.65), (0.06, 0.06, 0.06), mats["conveyor_belt"],
         name="To Lakehouse Conveyor (anchor)",
         entity_id="pipeline.to_lakehouse",
         entity_type="pipeline", stage_name="staging")

    # Both belts converge to Y=0 at the Lakehouse entrance via two Y-bends.
    # SILVER frames — feeding the Silver Lakehouse stage.
    build_conveyor_Y(stage, "/World/AccumulationPipeline/MainConverge_YBend",
                     y_start=-0.7, y_end=0.0, x_center=20.4,
                     z_top=0.7, width=1.0, mats=mats,
                     frame_mat_key="metal_silver")
    build_conveyor_Y(stage, "/World/AccumulationPipeline/ExpressConverge_YBend",
                     y_start=0.0, y_end=+0.7, x_center=20.4,
                     z_top=0.7, width=1.0, mats=mats,
                     frame_mat_key="metal_silver",
                     belt_mat_key="conveyor_belt_express")

    # ===== Zone 4: Lakehouse (Y=0, 17 x 12 x 6) — aligned with Raw on Y=0 =====
    lh_cx, lh_cy, lh_cz = 29.0, 0.0, 0.10
    lh_sx, lh_sy, lh_sz = 17.0, 12.0, 6.0
    cube(stage, "/World/Lakehouse/SilverLakehouse",
         (lh_cx, lh_cy, lh_cz),
         (lh_sx, lh_sy, 0.18), mats["concrete"],
         name="Silver Lakehouse", entity_id="lakehouse.silver",
         entity_type="storage_zone", stage_name="staging")
    # Lakehouse openings:
    #   left  (X-): for audit incoming at Y=0
    #   right (X+): for cold belt outgoing to docks at Y=0
    #   back  (Y+): for promotion belt up to Showcase at X=25
    build_warehouse(stage, "/World/Lakehouse",
                    center=(lh_cx, lh_cy, lh_cz + 0.10),
                    size=(lh_sx, lh_sy, lh_sz),
                    wall_mat=mats["glass_lakehouse"], frame_mat=mats["steel_frame"],
                    left_gap=(0.0, 1.4, 1.1),
                    right_gap=(0.0, 1.4, 1.1),
                    back_gap=(0.0, 1.4, 1.1))
    # Storage tables inside (5 cols x 4 rows = 20 tables) — fills the larger warehouse
    UsdGeom.Scope.Define(stage, "/World/Lakehouse/Tables")
    table_xs = [lh_cx - 7.5, lh_cx - 3.75, lh_cx, lh_cx + 3.75, lh_cx + 7.5]
    table_ys = [lh_cy - 5.0, lh_cy - 1.7, lh_cy + 1.7, lh_cy + 5.0]
    table_idx = 0
    for ri, ty in enumerate(table_ys):
        for ci, tx in enumerate(table_xs):
            table_idx += 1
            led_choice = (["green", "green", "yellow"]
                          if (ri + ci) % 4 == 0 else
                          (["green", "red", "green"] if (ri + ci) % 7 == 0 else
                           ["green", "green", "green"]))
            n_boxes = 3 if (ri + ci) % 2 == 0 else 2
            build_storage_table(stage,
                                f"/World/Lakehouse/Tables/Table_{table_idx}",
                                (tx, ty), mats,
                                n_boxes=n_boxes, leds=led_choice)
    # Lineage rays demo (3 thin colored beams between tables)
    UsdGeom.Scope.Define(stage, "/World/Lakehouse/LineageRays")
    cube(stage, "/World/Lakehouse/LineageRays/Ray_Table_1",
         (lh_cx - 1.6, lh_cy - 2.2, lh_cz + 1.20),
         (3.0, 0.04, 0.04), mats["lineage_table"])
    cube(stage, "/World/Lakehouse/LineageRays/Ray_Column_1",
         (lh_cx, lh_cy + 0.0, lh_cz + 1.25),
         (4.0, 0.04, 0.04), mats["lineage_column"])
    cube(stage, "/World/Lakehouse/LineageRays/Ray_Impact_1",
         (lh_cx + 1.6, lh_cy + 2.2, lh_cz + 1.30),
         (3.0, 0.05, 0.05), mats["lineage_impact"])
    # Legacy compat shelves (tiny anchors)
    cube(stage, "/World/Lakehouse/StagingShelf1", (lh_cx, lh_cy - 2.2, 1.20),
         (0.05, 0.05, 0.05), mats["table_top"],
         name="Staging Shelf 1", entity_id="shelf.silver.1",
         entity_type="staging_shelf", stage_name="staging")
    cube(stage, "/World/Lakehouse/StagingShelf2", (lh_cx, lh_cy + 0.0, 1.20),
         (0.05, 0.05, 0.05), mats["table_top"],
         name="Staging Shelf 2", entity_id="shelf.silver.2",
         entity_type="staging_shelf", stage_name="staging")
    cube(stage, "/World/Lakehouse/StagingShelf3", (lh_cx, lh_cy + 2.2, 1.20),
         (0.05, 0.05, 0.05), mats["table_top"],
         name="Staging Shelf 3", entity_id="shelf.silver.3",
         entity_type="staging_shelf", stage_name="staging")

    # ===== Zone 5: Showcase (Y=+22, 17 x 12 x 6) — pushed further north so HPDA truck fits =====
    sc_cx, sc_cy, sc_cz = 29.0, 22.0, 0.10
    sc_sx, sc_sy, sc_sz = 17.0, 12.0, 6.0
    cube(stage, "/World/Showcase/Floor",
         (sc_cx, sc_cy, sc_cz),
         (sc_sx, sc_sy, 0.18), mats["white_panel"])
    # Showcase needs: south wall opening (front gap, Y- side) for incoming from Lakehouse promotion belt,
    #                 east wall opening for outgoing to docks (hot path)
    build_warehouse(stage, "/World/Showcase",
                    center=(sc_cx, sc_cy, sc_cz + 0.10),
                    size=(sc_sx, sc_sy, sc_sz),
                    wall_mat=mats["glass_showcase"], frame_mat=mats["steel_frame"],
                    right_gap=(0.0, 1.4, 1.1),
                    front_gap=(0.0, 1.4, 1.1))  # south opening for promotion belt
    # Living-room style cabinets — distributed across 3 rows (north wall, middle
    # freestanding, south wall) so the showcase doesn't feel wall-hugging only.
    UsdGeom.Scope.Define(stage, "/World/Showcase/Displays")
    # North row (against +Y wall, facing south)
    north_y = sc_cy + sc_sy / 2 - 0.9
    for i, (dx, pop) in enumerate([(sc_cx - 5.5, 5), (sc_cx + 5.5, 5)]):
        build_showcase_cabinet(stage,
                               f"/World/Showcase/Displays/CabinetN_{i + 1}",
                               dx, north_y, mats,
                               cab_w=4.5, cab_d=0.8, cab_h=2.4,
                               facing="south", popularity=pop)
    # Middle freestanding row (at sc_cy, facing south toward visitor approach)
    middle_y = sc_cy
    for i, (dx, pop) in enumerate([(sc_cx - 6.0, 4), (sc_cx, 5), (sc_cx + 6.0, 4)]):
        build_showcase_cabinet(stage,
                               f"/World/Showcase/Displays/CabinetM_{i + 1}",
                               dx, middle_y, mats,
                               cab_w=4.5, cab_d=0.8, cab_h=2.4,
                               facing="south", popularity=pop)
    # South row (against -Y wall, facing north)
    south_y = sc_cy - sc_sy / 2 + 0.9
    for i, (dx, pop) in enumerate([(sc_cx - 5.5, 4), (sc_cx + 5.5, 5)]):
        build_showcase_cabinet(stage,
                               f"/World/Showcase/Displays/CabinetS_{i + 1}",
                               dx, south_y, mats,
                               cab_w=4.5, cab_d=0.8, cab_h=2.4,
                               facing="north", popularity=pop)

    # ===== Lakehouse -> Showcase promotion belt (GOLD frame) =====
    # Belt runs Y from +6 (LH north wall) to +16 (SC south wall) at X=29
    build_conveyor_Y(stage, "/World/Lakehouse/PromotionConveyor",
                     y_start=+6.0, y_end=+16.0, x_center=29.0,
                     z_top=0.7, width=0.9, mats=mats,
                     frame_mat_key="metal_gold")

    # ===== Zone 0+7 MERGED: Lobby + Search Counter (previous design restored,
    # only X position moved into the open corridor between LH/SC east wall and
    # the big table; Y aligns with Big Table / HPC truck line)
    ls_cx, ls_cy = 44.0, 10.0
    build_lobby_entrance(stage, "/World/Lobby", cx=ls_cx, cy=ls_cy - 0.5, mats=mats)
    build_search_counter(stage, "/World/SearchCounter",
                         cx=ls_cx, cy=ls_cy + 3.0, mats=mats)
    cube(stage, "/World/Delivery/CustomerDesk", (ls_cx, ls_cy + 3.0, 0.55),
         (0.10, 0.10, 0.10), mats["operator"],
         name="Customer Desk (Lobby + Search Counter)",
         entity_id="customer.desk", entity_type="customer", stage_name="delivery")
    build_mannequin(stage, "/World/Avatars/Avatar_Admin",
                    (ls_cx - 2.5, ls_cy - 2.0, 0.10), "admin", mats)
    build_mannequin(stage, "/World/Avatars/Avatar_Researcher",
                    (ls_cx + 2.5, ls_cy - 2.0, 0.10), "researcher", mats)
    build_mannequin(stage, "/World/Avatars/Avatar_Operator",
                    (ls_cx - 1.8, ls_cy + 1.5, 0.10), "operator", mats)
    build_mannequin(stage, "/World/Avatars/Avatar_Viewer",
                    (ls_cx + 1.8, ls_cy + 0.5, 0.10), "viewer", mats)
    build_mannequin(stage, "/World/Avatars/Avatar_Librarian",
                    (ls_cx, ls_cy + 4.2, 0.10), "operator", mats)

    # ===== Zone 8: Delivery Yard — single big table + 3 STRAIGHT outgoing belts =====
    # Trucks and Big Table aligned with Lobby Y line: HPC = Lobby Y = +10
    dock_ys = [+6.0, +10.0, +14.0]
    dock_names = ["AI", "HPC", "HPDA"]
    truck_rear_x = 62.0
    big_table_cx, big_table_cy = 52.0, 10.0
    big_table_w, big_table_d = 4.0, 11.0   # wide enough in Y to cover all 3 truck lanes
    cube(stage, "/World/DeliveryYard/Asphalt",
         (66.0, +10.0, -0.02), (16.0, 14.0, 0.05), mats["asphalt"])

    # ---- Big consolidation table (replaces 3 per-dock tables) ----
    UsdGeom.Scope.Define(stage, "/World/DeliveryYard/BigTable")
    floor_z = 0.10
    table_top_z = 0.85
    leg_h = table_top_z - 0.05
    for sxs, sys_, lbl in [(-1, -1, "SW"), (-1, +1, "NW"),
                           (+1, -1, "SE"), (+1, +1, "NE")]:
        cube(stage, f"/World/DeliveryYard/BigTable/Leg_{lbl}",
             (big_table_cx + sxs * (big_table_w / 2 - 0.10),
              big_table_cy + sys_ * (big_table_d / 2 - 0.10),
              floor_z + leg_h / 2),
             (0.12, 0.12, leg_h), mats["table_leg"])
    cube(stage, "/World/DeliveryYard/BigTable/Top",
         (big_table_cx, big_table_cy, floor_z + table_top_z),
         (big_table_w, big_table_d, 0.10), mats["table_top"])
    # Decorative rails on the two long edges (silver = LH side, gold = SC side)
    cube(stage, "/World/DeliveryYard/BigTable/Rail_S",
         (big_table_cx, big_table_cy - big_table_d / 2 + 0.05,
          floor_z + table_top_z + 0.06),
         (big_table_w * 0.95, 0.08, 0.10), mats["metal_silver"])
    cube(stage, "/World/DeliveryYard/BigTable/Rail_N",
         (big_table_cx, big_table_cy + big_table_d / 2 - 0.05,
          floor_z + table_top_z + 0.06),
         (big_table_w * 0.95, 0.08, 0.10), mats["metal_gold"])
    # Sample boxes ready for dispatch — spread across the longer Y span
    box_top_z = floor_z + table_top_z + 0.05 + 0.20
    for i, (dx, dy, led) in enumerate([
        (-0.8, big_table_cy - 4.0, "green"),
        (+0.8, big_table_cy - 3.0, "yellow"),
        (-0.8, big_table_cy - 1.5, "green"),
        (+0.8, big_table_cy - 0.5, "green"),
        (-0.8, big_table_cy + 1.0, "yellow"),
        (+0.8, big_table_cy + 2.0, "green"),
        (-0.8, big_table_cy + 3.0, "green"),
        (+0.8, big_table_cy + 4.0, "red"),
    ]):
        make_iceberg_box(stage, f"/World/DeliveryYard/BigTable/Box_{i + 1}",
                         (big_table_cx + dx, dy, box_top_z),
                         (0.50, 0.36, 0.40), mats, led=led)

    # ---- ONE LH belt -> big table (south edge) — SILVER ----
    big_t_south = big_table_cy - big_table_d / 2  # +5.0
    big_t_north = big_table_cy + big_table_d / 2  # +10.0
    build_conveyor(stage, "/World/DeliveryYard/LH_Belt/X",
                   x_start=37.5, x_end=big_table_cx, y_center=0.0,
                   z_top=0.7, width=1.0, mats=mats,
                   frame_mat_key="metal_silver")
    build_conveyor_Y(stage, "/World/DeliveryYard/LH_Belt/Y",
                     y_start=0.0, y_end=big_t_south,
                     x_center=big_table_cx,
                     z_top=0.7, width=1.0, mats=mats,
                     frame_mat_key="metal_silver")

    # ---- ONE SC belt -> big table (north edge) — GOLD ----
    # SC now at cy=+22, east wall exit at Y=+22.
    build_conveyor(stage, "/World/DeliveryYard/SC_Belt/X",
                   x_start=37.5, x_end=big_table_cx, y_center=+22.0,
                   z_top=0.7, width=1.0, mats=mats,
                   frame_mat_key="metal_gold")
    build_conveyor_Y(stage, "/World/DeliveryYard/SC_Belt/Y",
                     y_start=big_t_north, y_end=+22.0,
                     x_center=big_table_cx,
                     z_top=0.7, width=1.0, mats=mats,
                     frame_mat_key="metal_gold")

    # ---- 3 STRAIGHT outgoing belts: big table east edge -> each truck (no bends) ----
    # Big Table now wide enough in Y to cover all 3 truck Y lanes, so each belt is
    # a single straight east-going segment from table east edge to truck rear.
    big_t_east = big_table_cx + big_table_w / 2  # +54
    for nm, dy in zip(dock_names, dock_ys):
        build_conveyor(stage, f"/World/DeliveryYard/OutBelt_{nm}",
                       x_start=big_t_east, x_end=truck_rear_x - 0.5, y_center=dy,
                       z_top=0.7, width=0.9, mats=mats,
                       frame_mat_key="conveyor_promotion")

    # ---- Trucks parked east (cab +X, open rear at truck_rear_x) ----
    build_ai_truck(stage, "/World/DeliveryYard/Vehicle_AI",
                   truck_rear_x, dock_ys[0], mats)
    build_hpc_van(stage, "/World/DeliveryYard/Vehicle_HPC",
                  truck_rear_x, dock_ys[1], mats)
    build_hpda_van(stage, "/World/DeliveryYard/Vehicle_HPDA",
                   truck_rear_x, dock_ys[2], mats)

    workloads = [
        ("AI",   truck_rear_x + 2.0, dock_ys[0], "workload.ai.001"),
        ("HPC",  truck_rear_x + 2.0, dock_ys[1], "workload.hpc.001"),
        ("HPDA", truck_rear_x + 2.0, dock_ys[2], "workload.hpda.001"),
        ("MS",   truck_rear_x + 2.0, dock_ys[0] - 4.0, "workload.ms.001"),
    ]
    for nm, x, y, eid in workloads:
        cube(stage, f"/World/WorkloadInterfaces/{nm}", (x, y, 0.95),
             (0.10, 0.10, 0.10), mats["workload"],
             name=f"{nm} Interface", entity_id=eid,
             entity_type="workload_interface", stage_name="serving")

    # ===== Dataset Package protagonist =====
    dataset = cube(stage, "/World/Datasets/DatasetPackage001",
                   (-17.5, 0, 0.95), (0.60, 0.42, 0.42), mats["dataset_raw"],
                   name="Dataset Package 001", entity_id="dataset.sample.001",
                   entity_type="dataset", stage_name="raw")
    dp = dataset.GetPrim()
    dp.CreateAttribute("trident:metadata_status", Sdf.ValueTypeNames.String).Set("none")
    dp.CreateAttribute("trident:sharing_status", Sdf.ValueTypeNames.String).Set("private")
    dp.CreateAttribute("trident:quality_score", Sdf.ValueTypeNames.Float).Set(0.71)
    dp.CreateAttribute("trident:access_frequency", Sdf.ValueTypeNames.Int).Set(0)
    cube(stage, "/World/Datasets/DatasetPackage001/ExplainingMetadataTag",
         (0, 0.52, 0.46), (0.30, 0.05, 0.22), mats["metadata_explain"],
         name="Explaining Metadata Tag",
         entity_id="metadata.explaining.dataset.sample.001",
         entity_type="metadata", stage_name="explaining")
    cube(stage, "/World/Datasets/DatasetPackage001/SharingMetadataTag",
         (0, -0.52, 0.46), (0.30, 0.05, 0.22), mats["metadata_share"],
         name="Sharing Metadata Tag",
         entity_id="metadata.sharing.dataset.sample.001",
         entity_type="metadata", stage_name="sharing")

    # ===== Cameras =====
    cam_overview = UsdGeom.Camera.Define(stage, "/World/Camera")
    UsdGeom.XformCommonAPI(cam_overview).SetTranslate(Gf.Vec3d(25, -34, 32))
    UsdGeom.XformCommonAPI(cam_overview).SetRotate(Gf.Vec3f(58, 0, 0))
    cam_overview.CreateFocalLengthAttr(15)

    cam_pipeline = UsdGeom.Camera.Define(stage, "/World/Camera_Pipeline")
    UsdGeom.XformCommonAPI(cam_pipeline).SetTranslate(Gf.Vec3d(13.0, -8, 7))
    UsdGeom.XformCommonAPI(cam_pipeline).SetRotate(Gf.Vec3f(70, 0, 0))
    cam_pipeline.CreateFocalLengthAttr(24)

    cam_storage = UsdGeom.Camera.Define(stage, "/World/Camera_Storage")
    UsdGeom.XformCommonAPI(cam_storage).SetTranslate(Gf.Vec3d(29.0, -14, 18))
    UsdGeom.XformCommonAPI(cam_storage).SetRotate(Gf.Vec3f(52, 0, 0))
    cam_storage.CreateFocalLengthAttr(20)

    cam_delivery = UsdGeom.Camera.Define(stage, "/World/Camera_Delivery")
    UsdGeom.XformCommonAPI(cam_delivery).SetTranslate(Gf.Vec3d(62.0, -10, 10))
    UsdGeom.XformCommonAPI(cam_delivery).SetRotate(Gf.Vec3f(60, 0, 0))
    cam_delivery.CreateFocalLengthAttr(24)

    stage.SetDefaultPrim(stage.GetPrimAtPath("/World"))
    stage.GetRootLayer().Save()
    print(f"created {OUT}")


if __name__ == "__main__":
    main()
    simulation_app.close()
