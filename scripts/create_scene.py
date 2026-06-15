"""
Trident-Twin Data Readiness scene generator.

The scene vocabulary follows README.md:
  - Raw Bucket contains untagged brown source-object boxes.
  - Refinement Pipeline shows seven compact operation steps from audit/catalog to bundle/delivery; table crates carry thin readiness bars.
  - Lakehouse Inventory exposes actual resource inventory prims grouped by
    namespace/component, with counts, metadata coverage, freshness, quality,
    and workload fit stored as trident:* custom attributes.
  - Staging / Ready Bundles is not a second warehouse; it is a curated
    ready-to-use shelf for Portal Dataset Basket, hot collections, recommended
    joins, and materialized collections.
  - Search / Selection and Workload Delivery prims are explicit handoff surfaces
    for future Portal <-> Twin synchronization.
"""

from isaacsim import SimulationApp
simulation_app = SimulationApp({"headless": True})

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from pxr import Usd, UsdGeom, UsdShade, UsdLux, Sdf, Gf

# ---------------------------------------------------------------------------
# stats-service 동적 Raw Bucket 네임스페이스 조회
# 환경변수:
#   TRIDENT_STATS_BASE_URL  — stats-service 주소 (없으면 fallback 목록 사용)
#   TRIDENT_KC_URL          — Keycloak token endpoint
#   TRIDENT_KC_CLIENT_ID    — client id (기본: trident-baseline-runner)
#   TRIDENT_KC_CLIENT_SECRET
# ---------------------------------------------------------------------------
_FALLBACK_NAMESPACES = [
    "autonomous-driving-nuscenes", "autonomous_test", "ecommerce-orders",
    "finance-transactions", "genomics-vcf-archive", "iot-sensor-telemetry",
    "lidar-pointcloud-raw", "medical-imaging-chest-xray", "mimic-iv-demo-csv",
    "mimic-iv-demo", "nyc-taxi-trips", "polaris-verify",
    "satellite-imagery-sentinel", "surveillance-video-clips",
    "synthetic-driving", "weather-radar-archive",
]


DEFAULT_TWIN_HUB_URL = os.getenv("TWIN_HUB_URL", os.getenv("TRIDENT_TWIN_HUB_URL", "http://10.38.38.223:8765")).rstrip("/")


def _fetch_raw_namespaces() -> tuple[list[str], set[str]]:
    """Return live raw namespaces and ready/indexed namespace set.

    Prefer TWIN_HUB_URL so Isaac scene generation can use the deployed hub
    without carrying Keycloak secrets. Fall back to direct stats-service access,
    then to checked-in legacy fixtures.
    """
    twin_hub = DEFAULT_TWIN_HUB_URL
    if twin_hub:
        try:
            req = urllib.request.Request(f"{twin_hub}/api/twin/entities")
            with urllib.request.urlopen(req, timeout=8) as r:
                payload = json.loads(r.read())
            raw_entities = [e for e in payload.get("entities", []) if e.get("type") == "raw_bucket"]
            namespaces = sorted({str(e.get("namespace") or e.get("id", "").removeprefix("raw.")) for e in raw_entities if e.get("namespace") or e.get("id")})
            indexed = {str(e.get("namespace")) for e in raw_entities if str(e.get("status", "")).upper() in {"PASS", "OK", "DONE"}}
            if namespaces:
                print(f"[create_scene] twin-hub raw namespaces {len(namespaces)} loaded from {twin_hub}")
                return namespaces, indexed
        except Exception as e:
            print(f"[create_scene] twin-hub namespace 조회 실패: {e} — stats-service fallback")

    base = os.getenv("TRIDENT_STATS_BASE_URL", "").rstrip("/")
    if not base:
        print("[create_scene] TRIDENT_STATS_BASE_URL/TWIN_HUB_URL 미설정 — fallback 네임스페이스 사용")
        return _FALLBACK_NAMESPACES, {"autonomous_test", "autonomous_weather"}

    # Keycloak 토큰 발급
    token = os.getenv("TRIDENT_STATS_TOKEN", "")
    kc_url = os.getenv("TRIDENT_KC_URL", "")
    kc_id = os.getenv("TRIDENT_KC_CLIENT_ID", "trident-baseline-runner")
    kc_secret = os.getenv("TRIDENT_KC_CLIENT_SECRET", "")
    if not token and kc_url and kc_secret:
        try:
            data = urllib.parse.urlencode({
                "grant_type": "client_credentials",
                "client_id": kc_id,
                "client_secret": kc_secret,
            }).encode()
            req = urllib.request.Request(
                kc_url, data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"})
            with urllib.request.urlopen(req, timeout=8) as r:
                token = json.loads(r.read())["access_token"]
        except Exception as e:
            print(f"[create_scene] Keycloak 토큰 발급 실패: {e} — fallback 사용")
            return _FALLBACK_NAMESPACES, {"autonomous_test", "autonomous_weather"}

    headers = {"Authorization": f"Bearer {token}"} if token else {}

    def _get(path: str):
        req = urllib.request.Request(f"{base}{path}", headers=headers)
        with urllib.request.urlopen(req, timeout=6) as r:
            return json.loads(r.read())

    try:
        s3 = _get("/stats/s3/list?bucket=trident-raw&prefix=&delimiter=/")
        namespaces = [d["name"] for d in s3.get("dirs", [])]
        if not namespaces:
            raise ValueError("빈 응답")
    except Exception as e:
        print(f"[create_scene] S3 목록 조회 실패: {e} — fallback 사용")
        return _FALLBACK_NAMESPACES, {"autonomous_test", "autonomous_weather"}

    try:
        audit = _get("/stats/audit")
        indexed = {row["namespace"] for row in audit if str(row.get("status", "")).upper() in {"PASS", "OK", "DONE"}}
    except Exception:
        indexed = set()

    print(f"[create_scene] Raw Bucket 네임스페이스 {len(namespaces)}개 로드 (인덱싱 완료: {len(indexed)}개)")
    return namespaces, indexed

BASE = Path(__file__).resolve().parents[1]
_ts = datetime.now().strftime("%Y%m%d_%H%M")
OUT = BASE / "stages" / f"trident_lakehouse_twin_{_ts}.usda"

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
    "lakehouse_data_table": ((0.38, 0.72, 1.00), 1.00),
    "lakehouse_metadata_table": ((1.00, 0.78, 0.22), 1.00),
    "lakehouse_slot_base": ((0.70, 0.74, 0.78), 1.00),
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
    # Data Readiness vocabulary
    "schema_bar":         ((0.10, 0.45, 0.95), 1.00),  # blue: Iceberg schema/table appears
    "quality_bar":        ((0.95, 0.82, 0.12), 1.00),  # yellow: quality/integrity measured
    "semantic_tag":       ((0.55, 0.25, 0.85), 1.00),  # purple: Milvus semantic index
    "location_tag":       ((0.10, 0.70, 0.95), 1.00),  # cyan: location/path metadata
    "policy_tag":         ((0.15, 0.75, 0.25), 1.00),  # green: policy/share-ready
    "freshness_tag":      ((0.10, 0.70, 0.95), 1.00),
    "quality_badge":      ((0.20, 0.95, 0.30), 1.00),
    "process_step":       ((0.22, 0.24, 0.28), 1.00),
    "process_output":     ((0.94, 0.95, 0.97), 1.00),
    "process_pending":    ((0.35, 0.35, 0.38), 1.00),
    "bundle_tray":        ((1.00, 0.78, 0.15), 1.00),
    "bundle_payload":     ((1.00, 0.93, 0.55), 1.00),
    "search_highlight":   ((0.05, 0.75, 0.90), 0.38),
    "bottleneck_warn":    ((1.00, 0.55, 0.05), 1.00),
    "delivery_package":   ((0.60, 0.35, 0.95), 1.00),
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


def set_trident_attrs(prim, **attrs):
    """Attach stable Trident metadata to a USD prim."""
    p = prim.GetPrim() if hasattr(prim, "GetPrim") else prim
    for key, value in attrs.items():
        if value is None:
            continue
        name = key if key.startswith("trident:") else f"trident:{key}"
        if isinstance(value, bool):
            t = Sdf.ValueTypeNames.Bool
        elif isinstance(value, int) and not isinstance(value, bool):
            t = Sdf.ValueTypeNames.Int
        elif isinstance(value, float):
            t = Sdf.ValueTypeNames.Float
        else:
            t = Sdf.ValueTypeNames.String
            value = str(value)
        attr = p.GetAttribute(name) or p.CreateAttribute(name, t)
        attr.Set(value)
    return p


def define_scope(stage, path, **attrs):
    scope = UsdGeom.Scope.Define(stage, path)
    set_trident_attrs(scope, **attrs)
    return scope


def zone_pad(stage, path, center, size, color_mat):
    """Colored floor slab marking the zone footprint (no signposts)."""
    cx, cy = center
    sx, sy = size
    cube(stage, path, (cx, cy, 0.012), (sx, sy, 0.024), color_mat)


# ============================================================================
# Flat ground text — 5x7 pixel block alphabet, painted as thin cubes on floor.
# Used for zone labels (INGEST ZONE / RAW BUCKET ZONE / ...) and truck labels.
# ============================================================================
ALPHABET_5x7 = {
    "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
    "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
    "C": ["01111", "10000", "10000", "10000", "10000", "10000", "01111"],
    "D": ["11110", "10001", "10001", "10001", "10001", "10001", "11110"],
    "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
    "G": ["01111", "10000", "10000", "10011", "10001", "10001", "01111"],
    "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
    "I": ["11111", "00100", "00100", "00100", "00100", "00100", "11111"],
    "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
    "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
    "M": ["10001", "11011", "10101", "10001", "10001", "10001", "10001"],
    "N": ["10001", "11001", "10101", "10101", "10101", "10011", "10001"],
    "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
    "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
    "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
    "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
    "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
    "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
    "V": ["10001", "10001", "10001", "01010", "01010", "00100", "00100"],
    "W": ["10001", "10001", "10001", "10001", "10101", "11011", "10001"],
    "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
    "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
    "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
}


def render_text(stage, root_path, text, center, mats,
                pixel=0.12, height_z=0.04, color_key="black_panel"):
    """Render TEXT flat on the ground at `center`, centered horizontally.

    Text reads west-to-east (along +X), characters lying down so the camera
    looking from -Y sees them right-side-up.
    """
    UsdGeom.Scope.Define(stage, root_path)
    cx, cy, cz = center
    char_w = 5 * pixel
    char_h = 7 * pixel
    gap = pixel
    chars = list(text.upper())
    total_w = sum(char_w if c != " " else char_w * 0.6 for c in chars) + gap * max(0, len(chars) - 1)
    x = cx - total_w / 2
    mat = mats[color_key]
    cube_z = cz + height_z / 2
    for ci, ch in enumerate(chars):
        if ch == " ":
            x += char_w * 0.6 + gap
            continue
        pattern = ALPHABET_5x7.get(ch)
        if pattern is None:
            x += char_w + gap
            continue
        for r, line in enumerate(pattern):
            for c, p in enumerate(line):
                if p != "1":
                    continue
                px = x + c * pixel + pixel / 2
                py = cy + ((6 - r) - 3) * pixel  # row 0 = top (north)
                cube(stage, f"{root_path}/C{ci}_R{r}_C{c}",
                     (px, py, cube_z),
                     (pixel * 0.92, pixel * 0.92, height_z), mat)
        x += char_w + gap


# ============================================================================
# Box helpers
# ============================================================================
def make_raw_box(stage, path, pos, scale, mats, dark=False):
    mat = mats["raw_box_dark"] if dark else mats["raw_box"]
    return cube(stage, path, pos, scale, mat)


GATE_BADGES = [
    ("INGEST",  "metal_bronze"),
    ("STAGE",   "metal_silver"),
    ("CLEAN",   "quality_bar"),
    ("TAG",     "semantic_tag"),
    ("CATALOG", "policy_tag"),
]

def add_gate_badges(stage, path, pos, scale, mats):
    sx, sy, sz = scale
    badge_w = sx * 0.14
    badge_d = sy * 0.14
    badge_t = 0.018
    spacing = sx * 0.19
    x0 = pos[0] - spacing * 2
    for i, (gname, gmat) in enumerate(GATE_BADGES):
        cube(stage, f"{path}/GateBadges/{gname}",
             (x0 + i * spacing, pos[1], pos[2] + sz / 2 + badge_t / 2 + 0.004),
             (badge_w, badge_d, badge_t), mats[gmat])


def make_iceberg_box(stage, path, pos, scale, mats, led="green"):
    xform = UsdGeom.Xform.Define(stage, path)
    cube(stage, f"{path}/Body", pos, scale, mats["iceberg_box"])
    add_gate_badges(stage, path, pos, scale, mats)
    return xform.GetPrim()




def make_readiness_table_crate(stage, path, pos, scale, mats, *,
                               entity_id, namespace, component, row_count,
                               object_count, quality_score, access_frequency,
                               semantic=True, location=True, policy=True,
                               freshness="fresh", workload_fit="AI",
                               table_role="data"):
    """Create a live-bindable Lakehouse Inventory table crate.

    The body is the refined Iceberg table; thin top bars show schema, quality, semantic, location, and policy readiness without cluttering each crate.
    """
    UsdGeom.Xform.Define(stage, path)
    sx, sy, sz = scale
    role = "metadata" if str(table_role).lower() == "metadata" else "data"
    body_mat = mats["lakehouse_metadata_table" if role == "metadata" else "lakehouse_data_table"]
    body = cube(stage, f"{path}/TableCrate", pos, scale, body_mat,
                name=f"{namespace}.{component} {role} table crate",
                entity_id=entity_id, entity_type="iceberg_table",
                stage_name="lakehouse_inventory")
    set_trident_attrs(
        body, zone="zone.lakehouse_inventory", namespace=namespace,
        component=component, table_role=role, row_count=row_count, object_count=object_count,
        quality_score=quality_score, access_frequency=access_frequency,
        semantic_ready=semantic, location_ready=location, policy_ready=policy,
        freshness=freshness, workload_fit=workload_fit, readiness_score=quality_score,
    )
    add_gate_badges(stage, path, pos, scale, mats)
    return body


def make_ready_bundle(stage, path, pos, mats, *, entity_id, name, components,
                      workload_fit, confidence, access_frequency, policy_ready=True):
    """Create a Staging / Ready Bundles tray for fast user selection."""
    UsdGeom.Xform.Define(stage, path)
    tray = cube(stage, f"{path}/Tray", pos, (1.65, 0.95, 0.12), mats["bundle_tray"],
                name=name, entity_id=entity_id, entity_type="ready_bundle",
                stage_name="ready_bundle")
    set_trident_attrs(tray, zone="zone.staging_ready_bundles",
                      components=components, workload_fit=workload_fit,
                      confidence=confidence, access_frequency=access_frequency,
                      policy_ready=policy_ready, readiness_score=confidence)
    # Payload blocks show the joined/curated datasets inside the bundle.
    for i, comp in enumerate(components.split("+")):
        cube(stage, f"{path}/Payload/{comp.strip().title()}_{i + 1}",
             (pos[0] - 0.45 + i * 0.45, pos[1], pos[2] + 0.22),
             (0.34, 0.42, 0.28), mats["bundle_payload"],
             name=f"{comp.strip()} payload", entity_id=f"{entity_id}.payload.{comp.strip()}",
             entity_type="bundle_payload", stage_name="ready_bundle")
    cyl(stage, f"{path}/ConfidenceBadge",
        (pos[0] + 0.68, pos[1] + 0.35, pos[2] + 0.35),
        0.08, 0.05, "Z", mats["quality_badge" if confidence >= 0.85 else "bottleneck_warn"])
    set_trident_attrs(stage.GetPrimAtPath(f"{path}/ConfidenceBadge"),
                      entity_id=f"{entity_id}.confidence", entity_type="readiness_badge",
                      confidence=confidence, workload_fit=workload_fit)
    return tray


def make_search_highlight(stage, path, pos, scale, mats, *, entity_id, query, candidate_count):
    prim = cube(stage, path, pos, scale, mats["search_highlight"],
                name=f"Search intent highlight: {query}", entity_id=entity_id,
                entity_type="search_highlight", stage_name="selection")
    set_trident_attrs(prim, zone="zone.search_selection", query=query,
                      candidate_count=candidate_count, selection_state="candidate_highlight")
    return prim


def make_delivery_package(stage, path, pos, mats, *, entity_id, workload_type, snippet_type, source_bundle):
    prim = cube(stage, path, pos, (0.72, 0.48, 0.36), mats["delivery_package"],
                name=f"{workload_type} delivery package", entity_id=entity_id,
                entity_type="workload_delivery_package", stage_name="workload_delivery")
    set_trident_attrs(prim, zone="zone.workload_delivery", workload_type=workload_type,
                      snippet_type=snippet_type, source_bundle=source_bundle,
                      delivery_ready=True)
    return prim

def make_pipeline_operation_step(stage, path, pos, mats, *, step_no, code_label, operation, output_kind, output_entity, bar_mat_key):
    """Security-gate style checkpoint on the belt.

    Visual: two upright pillars straddling the belt + horizontal crossbar +
    a colored tag badge hanging from the crossbar. No text labels.
    trident:* attributes are stamped on the gate root prim for live binding.
    """
    UsdGeom.Xform.Define(stage, path)
    x, y, z = pos

    # Gate root — carries all trident:* attrs for live binding
    gate = cube(stage, f"{path}/Gate", (x, y, z - 0.3), (0.05, 0.05, 0.05), mats["process_step"],
                name=f"Step {step_no}: {operation}",
                entity_id=f"operation.{step_no:02d}.{operation}",
                entity_type="pipeline_operation", stage_name=operation)
    set_trident_attrs(gate, step_no=step_no, operation=operation,
                      output_kind=output_kind, output_entity=output_entity,
                      zone="zone.refinement_pipeline")

    # Pillars span both belts (belt centers at y=-0.7 and y=+0.7 relative to gate center y=0)
    # Outer edge of rails ≈ y=±1.25; pillars placed at y=±1.8 for clearance.
    cube(stage, f"{path}/PillarL", (x, y - 1.35, z + 1.00), (0.10, 0.10, 2.0), mats["steel_frame"])
    cube(stage, f"{path}/PillarR", (x, y + 1.35, z + 1.00), (0.10, 0.10, 2.0), mats["steel_frame"])
    cube(stage, f"{path}/Crossbar", (x, y, z + 2.08), (0.10, 2.9, 0.10), mats["steel_frame"])
    # Colored badge hanging center of crossbar
    cube(stage, f"{path}/Badge", (x, y, z + 1.78), (0.30, 0.30, 0.30), mats[bar_mat_key],
         name=f"{operation} badge",
         entity_id=f"operation.{step_no:02d}.{operation}.badge",
         entity_type="operation_badge", stage_name=operation)

    # code_label 텍스트 — PillarL 앞 바닥면에 작게 배치
    render_text(stage, f"{path}/Label", code_label,
                (x, y - 1.60, z + 0.02), mats,
                pixel=0.032, height_z=0.02, color_key="black_panel")

    return gate

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
    for i, (role, color_key) in enumerate([
        ("admin",      "role_admin"),
        ("operator",   "role_operator"),
        ("researcher", "role_researcher"),
        ("viewer",     "role_viewer"),
        ("service",    "role_service"),
    ]):
        sphere(stage, f"{root_path}/IndicatorPanel/Role_{role}",
               (cx - 1.0 + i * 0.50, cy + 0.27, panel_z),
               0.18, mats[color_key])
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
    sphere(stage, f"{root_path}/RoleBadge", (x, y, z + 2.20), 0.12, mats[role_colors[role]])


# ============================================================================
# Live Lakehouse inventory lookup
# ============================================================================
def _table_workload_fit(table: str, namespace: str) -> str:
    token = f"{namespace}.{table}".lower()
    if any(k in token for k in ("image", "radiology", "waveform")):
        return "AI+HPDA"
    if any(k in token for k in ("event", "score", "cohort", "lab", "vital")):
        return "HPDA"
    if any(k in token for k in ("manifest", "metadata", "catalog")):
        return "HPDA"
    return "AI+HPDA"


def _fetch_lakehouse_inventory_specs(max_tables: int = 64) -> list[dict]:
    """Return live table specs from twin-hub entities; fallback caller decides on empty."""
    if not DEFAULT_TWIN_HUB_URL:
        return []
    try:
        req = urllib.request.Request(f"{DEFAULT_TWIN_HUB_URL}/api/twin/entities")
        with urllib.request.urlopen(req, timeout=8) as r:
            payload = json.loads(r.read())
    except Exception as e:
        print(f"[create_scene] twin-hub lakehouse 조회 실패: {e} — inventory fallback")
        return []

    tables = [e for e in payload.get("entities", []) if e.get("type") == "iceberg_table"]
    specs: list[dict] = []
    seen: set[str] = set()
    for e in tables:
        entity_id = str(e.get("id") or "").lower()
        parts = entity_id.split(".")
        ns = str(e.get("namespace") or (parts[1] if len(parts) >= 3 else "default"))
        table = str((parts[2] if len(parts) >= 3 else "") or e.get("table") or e.get("name") or e.get("component") or "unknown")
        if "." in table:
            table = table.split(".")[-1]
        entity_id = entity_id or f"table.{ns}.{table}".lower()
        rel_path = f"{ns.title()}/{table.title()}".replace("-", "_").replace(".", "_")
        if rel_path in seen:
            continue
        seen.add(rel_path)
        readiness = float(e.get("readiness_score") or e.get("quality_score") or 0.85)
        specs.append({
            "rel_path": rel_path,
            "entity_id": entity_id,
            "namespace": ns,
            "component": table,
            "row_count": int(e.get("row_count") or 0),
            "object_count": int(e.get("object_count") or e.get("total_assets") or 0),
            "quality_score": round(max(0.0, min(1.0, readiness)), 2),
            "access_frequency": int(e.get("access_frequency") or 0),
            "semantic": e.get("semantic_ready") if isinstance(e.get("semantic_ready"), bool) else True,
            "location": e.get("location_ready") if isinstance(e.get("location_ready"), bool) else True,
            "policy": e.get("policy_ready") if isinstance(e.get("policy_ready"), bool) else True,
            "freshness": str(e.get("freshness") or "live"),
            "workload_fit": str(e.get("workload_fit") or _table_workload_fit(table, ns)),
        })
        if len(specs) >= max_tables:
            break
    print(f"[create_scene] twin-hub lakehouse tables {len(specs)} loaded from {DEFAULT_TWIN_HUB_URL}")
    return specs


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
        "/World/DataReadiness",
        "/World/DataReadiness/RawObjects",
        "/World/DataReadiness/Refinement",
        "/World/DataReadiness/ProcessFlow",
        "/World/DataReadiness/Inventory",
        "/World/DataReadiness/ReadyBundles",
        "/World/DataReadiness/SearchSelection",
        "/World/DataReadiness/WorkloadDelivery",
    ]:
        UsdGeom.Scope.Define(stage, scope)

    mats = {k: create_mat(stage, k, c, o) for k, (c, o) in COLORS.items()}

    set_trident_attrs(stage.GetPrimAtPath("/World/DataReadiness"),
                      entity_id="twin.data_readiness",
                      entity_type="readiness_twin_root",
                      purpose="spatial decision map for finding usable data",
                      source_of_truth="Iceberg/Nessie/Redis/Milvus/PostgreSQL/Stats Service")

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

    # ===== Zone floor pads (colored identification) + flat ground labels =====
    # Pads were widened in Y so the painted text fits comfortably below the zone content.
    # Warehouse: center=(cx,11), sy=32 → Y: -5~+27
    # Zone pads extend south to include label area (label at y=-7.5 → pad south edge at -9)
    # pad cy = (-9 + 27)/2 = 9, pad sy = 36
    zone_pad(stage, "/World/ZonePads/Tower",       (-22,  +25), (6,   6),  mats["zone_color_9"])
    # TruckYard: only the truck parking area
    zone_pad(stage, "/World/ZonePads/TruckYard",   (-22,   0),  (16,  8), mats["zone_color_2"])
    # RawBucket pad: south edge at y=-9 (covers label at -7.5), north edge at +27
    zone_pad(stage, "/World/ZonePads/RawBucket",   (-4.0,  9.0), (21.0, 38.0), mats["zone_color_2"])
    zone_pad(stage, "/World/ZonePads/Pipeline",    (+13,    0), (16, 10), mats["metal_silver"])
    # Lakehouse pad: same logic
    # Lakehouse 하단(Metadata/Storage): y=-10~13.5
    zone_pad(stage, "/World/ZonePads/LakehouseMeta",    (+29.0,  1.75), (21.0, 23.5), mats["metal_silver"])
    # Lakehouse 상단(Staging): y=13.5~28
    zone_pad(stage, "/World/ZonePads/LakehouseStaging", (+29.0, 20.75), (21.0, 14.5), mats["metal_gold"])
    zone_pad(stage, "/World/ZonePads/LobbySearch", (+44,  +10), (10, 14), mats["zone_color_0"])
    # Delivery pad: covers label(y~+3) + trucks(y=6~14, cab to x~68) + DELIVERY ZONE text
    # Delivery pad: trucks at y=6~14, label at y~+3, add margin → y=+2~+17
    zone_pad(stage, "/World/ZonePads/Delivery",    (+59,  +9.5), (22, 20), mats["zone_color_8"])

    # ----- Zone labels painted OUTSIDE (south of) each warehouse -----
    # Warehouse south edge: cy - sy/2 = 11 - 16 = -5. Labels at y=-7 (outside wall).
    render_text(stage, "/World/ZonePads/Labels/RawBucket",
                "RAW BUCKET ZONE",  (-4.0,  -7.5, 0.025), mats, pixel=0.13)
    render_text(stage, "/World/ZonePads/Labels/Refinement",
                "ACCUMULATION ZONE", (+13.0, -4.3, 0.025), mats, pixel=0.075)
    render_text(stage, "/World/ZonePads/Labels/Lakehouse",
                "LAKEHOUSE ZONE",   (+29.0, -7.5, 0.025), mats, pixel=0.12)
    render_text(stage, "/World/ZonePads/Labels/Staging",
                "STAGING ZONE",     (+29.0, +13.9, 0.025), mats, pixel=0.08)
    render_text(stage, "/World/ZonePads/Labels/Search",
                "SEARCH ZONE",      (+44.0,  +4.0, 0.025), mats, pixel=0.10)
    render_text(stage, "/World/ZonePads/Labels/Delivery",
                "DELIVERY ZONE",    (+59.0,  +2.6, 0.025), mats, pixel=0.13)
    render_text(stage, "/World/ZonePads/Labels/Tower",
                "TOWER",            (-22.0, +22.4, 0.025), mats, pixel=0.14)

    # ===== Zone 9: Control Tower (moved north to (-22, +25)) =====
    build_control_tower(stage, "/World/ControlTower", cx=-22.0, cy=+25.0, mats=mats)
    cube(stage, "/World/Operations/OperatorDesk", (-22.0, +25.5, 11.5),
         (0.10, 0.10, 0.10), mats["operator"],
         name="System Operator Desk (Control Tower)",
         entity_id="operator.control", entity_type="operator",
         stage_name="monitoring")

    # ===== Zone 1: Ingest / Truck Yard (no parking stripes) =====
    cube(stage, "/World/TruckYard/Asphalt", (-22.0, 0, -0.02),
         (14.0, 8.0, 0.05), mats["asphalt"])
    build_truck(stage, "/World/LoadingDock/Truck",
                trailer_rear_x=-18.0, y_center=0.0, mats=mats)

    # Inbound conveyor: long stretch from truck rear (-17.9) to Raw west wall (-12.5)
    # BRONZE frame — this belt feeds the Raw / Bronze stage.
    build_conveyor(stage, "/World/LoadingDock/InboundConveyor",
                   x_start=-17.9, x_end=-14.0, y_center=0.0,
                   z_top=0.7, width=1.0, mats=mats,
                   frame_mat_key="metal_bronze")

    # ===== Zone 2: Raw Bucket Warehouse (19 x 32 x 6, center Y=11) =====
    # Y range: 11-16=-5 ~ 11+16=+27. Labels at Y=-7.6 are visible south of warehouse.
    raw_cx, raw_cy, raw_cz = -4.0, 11.0, 0.10
    raw_sx, raw_sy, raw_sz = 19.0, 32.0, 6.0
    # BronzeLake 바닥 패드 제거 — 창고 콘크리트 바닥만 사용
    build_warehouse(stage, "/World/Lake",
                    center=(raw_cx, raw_cy, raw_cz + 0.10),
                    size=(raw_sx, raw_sy, raw_sz),
                    wall_mat=mats["glass_lake"], frame_mat=mats["steel_frame"],
                    left_gap=(-11.0, 2.0, 1.1), right_gap=(-11.0, 3.5, 1.1))
    # Brown raw boxes piled inside — one zone per S3 namespace (dynamic, 16 dirs).
    # Warehouse interior safe range: X -12~+4, Y -4~+26 (30m total).
    # 네임스페이스별 구역 — X축 방향으로 박스 수 비례 폭, 넘치면 다음 Y행.
    # 구역 이름은 각 구역 상단 (공중 텍스트, 벽 안쪽 높이 1.5m).
    UsdGeom.Scope.Define(stage, "/World/Lake/Contents")
    RAW_NAMESPACES, _INDEXED_NS = _fetch_raw_namespaces()

    _NS_SIZE_GIB: dict[str, float] = {
        "autonomous-driving-nuscenes": 1.0,
        "autonomous_test":             5.2,
        "ecommerce-orders":            0.4,
        "finance-transactions":        0.6,
        "genomics-vcf-archive":        1.0,
        "iot-sensor-telemetry":        0.6,
        "lidar-pointcloud-raw":        1.0,
        "medical-imaging-chest-xray":  1.0,
        "mimic-iv-demo-csv":           0.05,
        "mimic-iv-demo":               0.01,
        "nyc-taxi-trips":              0.7,
        "polaris-verify":              0.0,
        "satellite-imagery-sentinel":  1.0,
        "surveillance-video-clips":    1.0,
        "synthetic-driving":           0.0,
        "weather-radar-archive":       1.0,
    }
    # 네임스페이스 이름 그대로 사용 (하이픈/언더스코어 → 공백으로 변환해 2줄 분리 용이하게)
    def _ns_label(ns: str) -> str:
        return ns.replace("-", " ").replace("_", " ").upper()
    _NS_LABEL: dict[str, str] = {ns: _ns_label(ns) for ns in RAW_NAMESPACES}

    import math as _math

    # 창고 내부 안전 범위: X -12.5~+4.5 (17m), Y -4~+26 (30m)
    X_START = -12.5
    X_END   = +4.5
    Y_START = -4.0

    # 각 구역 고정 풋프린트: 3×3 박스
    COLS = 3          # X 방향 박스 열 수
    ROWS = 3          # Y 방향 박스 행 수
    MAX_LAYERS = 10   # 최대 쌓기 층수
    BOX_SZ  = (0.48, 0.48, 0.48)   # 박스 크기 (작게)
    GAP     = 0.08    # 박스 간 간격
    CELL    = BOX_SZ[0] + GAP      # 셀 크기 (0.56m)
    ZONE_W  = COLS * CELL          # 구역 X 폭 (1.68m)
    ZONE_D  = ROWS * CELL          # 구역 Y 깊이 (1.68m)
    LABEL_H = 0.50    # 이름 텍스트용 Y 여백 (구역 앞쪽)
    ZONE_TOTAL_D = ZONE_D + LABEL_H  # 구역 전체 Y (2.18m)
    ZONE_GAP_X = 0.15  # 구역 간 X 간격

    def n_boxes_for(ns: str) -> int:
        gib = _NS_SIZE_GIB.get(ns, 0.5)
        return max(1, min(COLS * ROWS * MAX_LAYERS, _math.ceil(gib)))

    # X축으로 구역 배치 — 행 넘치면 다음 Y행
    x_cur  = X_START
    y_row  = Y_START
    row_idx = 0
    raw_slot_centers: dict[str, tuple[float, float]] = {}

    for ns_i, ns in enumerate(RAW_NAMESPACES):
        safe_ns = ns.replace("-", "_")
        indexed = ns in _INDEXED_NS
        n = n_boxes_for(ns)

        # 행 넘침 체크
        if x_cur + ZONE_W > X_END + 0.05 and x_cur > X_START:
            # Y 행 경계선 (이전 행 상단)
            y_div = Y_START + row_idx * (ZONE_TOTAL_D + 0.20) + ZONE_TOTAL_D
            cube(stage, f"/World/DataReadiness/RawObjects/DivY_{row_idx}",
                 ((X_START + X_END) / 2, y_div, 0.15),
                 (X_END - X_START, 0.03, 0.25), mats["steel_frame"])
            x_cur   = X_START
            row_idx += 1
            y_row   = Y_START + row_idx * (ZONE_TOTAL_D + 0.20)

        x_lo = x_cur
        y_lo = y_row  # 이름 텍스트 영역 시작
        y_box_start = y_lo + LABEL_H  # 박스 시작 Y

        raw_slot_centers[ns] = (x_lo + ZONE_W / 2, y_box_start + ZONE_D / 2)

        # 구역 X 구분선 (첫 구역 제외): 바닥 위 얇은 판
        if x_cur > X_START:
            cube(stage, f"/World/DataReadiness/RawObjects/DivX_{ns_i}",
                 (x_lo - ZONE_GAP_X / 2, y_lo + ZONE_TOTAL_D / 2, 0.15),
                 (0.03, ZONE_TOTAL_D, 0.25), mats["steel_frame"])

        # 구역 이름: ZONE_W 안에 맞게 pixel 자동 계산
        # render_text 글자폭 = 5*pixel, 공백 = 3*pixel, gap = pixel
        # 최대 한 줄 폭 = ZONE_W - 0.06 (여백)
        label_full = _NS_LABEL.get(ns, ns.upper())
        # 단어를 절반씩 2줄로 분리 (3단어면 2/1, 4단어면 2/2 등)
        words = label_full.split()
        split = max(1, len(words) // 2 + len(words) % 2)
        line1 = " ".join(words[:split])
        line2 = " ".join(words[split:]) if len(words) > split else ""

        # render_text total_w 공식: 각 글자 5px + gap(1px), 공백 3px + gap(1px)
        # total_w = sum(5+1 per char, 3+1 per space) - 1 (마지막 gap 없음)
        def _pixel_for(text: str, max_w: float) -> float:
            chars = list(text)
            slots = sum(6 if c != " " else 4 for c in chars) - 1
            return (max_w - 0.10) / max(slots, 1)

        longer = line1 if len(line1) >= len(line2) else line2
        px = min(0.026, _pixel_for(longer, ZONE_W))

        lx = x_lo + ZONE_W / 2   # 구역 X 중앙 (render_text가 중앙 정렬)
        # 위에서부터: Y 큰 쪽(구역 뒤)에서 시작해 아래로 내림
        ly1 = y_lo + LABEL_H - px * 9
        ly2 = ly1 - px * 9

        render_text(stage,
                    f"/World/DataReadiness/RawObjects/{safe_ns}/Label1",
                    line1, (lx, ly1, 0.025),
                    mats, pixel=px, height_z=0.018,
                    color_key="black_panel")
        if line2:
            render_text(stage,
                        f"/World/DataReadiness/RawObjects/{safe_ns}/Label2",
                        line2, (lx, ly2, 0.025),
                        mats, pixel=px, height_z=0.018,
                        color_key="black_panel")

        # 박스 3D 배치: col(X) × row(Y) × layer(Z)
        slots = COLS * ROWS
        for b_i in range(n):
            layer = b_i // slots
            slot  = b_i % slots
            col   = slot % COLS
            row   = slot // COLS
            bx = x_lo + col * CELL + CELL / 2
            by = y_box_start + row * CELL + CELL / 2
            bz = BOX_SZ[2] / 2 + 0.01 + layer * (BOX_SZ[2] + 0.02)
            dark = not indexed and (layer % 2 == 1)
            raw = make_raw_box(stage,
                               f"/World/DataReadiness/RawObjects/{safe_ns}/Box_{b_i}",
                               (bx, by, bz), BOX_SZ, mats, dark=dark)
            set_trident_attrs(raw, entity_id=f"raw.{ns}",
                              entity_type="raw_bucket", zone="zone.raw_bucket",
                              stage="raw_ingestion", metadata_status="none",
                              semantic_ready=False, location_ready=False,
                              policy_ready=False,
                              readiness_score=1.0 if indexed else 0.05)

        x_cur = x_lo + ZONE_W + ZONE_GAP_X
    # Compatibility aliases under the older /World/Lake path are intentionally
    # not created as separate boxes; /World/DataReadiness/RawObjects is the
    # canonical raw-object vocabulary for live bindings.

    # No conveyor inside Raw Bucket — boxes simply rest there as storage.
    # Two parallel SAME-SIZE belts (Main + Express) start at Raw east wall
    # and run all the way through the pipeline stations to Lakehouse west.

    # ===== Zone 3: Accumulation Zone =====
    # 7 catalog-first security gates, one per station_x position, straddling BOTH belts together.
    # Belt centers: y=-0.7 and y=+0.7. Gate spans both belts (pillars at y=±1.8).
    station_x = [6.6, 8.4, 10.2, 12.0, 13.8, 15.6, 17.4]
    UsdGeom.Scope.Define(stage, "/World/Pipeline")

    # Main belt — starts just east of Raw east wall (+5.5), Y=-0.7. SILVER frame.
    build_conveyor(stage, "/World/AccumulationPipeline/InputConveyor",
                   x_start=5.8, x_end=19.4, y_center=-0.7,
                   z_top=0.7, width=1.0, mats=mats,
                   frame_mat_key="metal_silver")
    p = stage.GetPrimAtPath("/World/AccumulationPipeline/InputConveyor")
    p.CreateAttribute("trident:entity_id", Sdf.ValueTypeNames.String).Set("pipeline.accumulation")
    p.CreateAttribute("trident:entity_type", Sdf.ValueTypeNames.String).Set("pipeline")
    p.CreateAttribute("trident:stage", Sdf.ValueTypeNames.String).Set("accumulation")
    p.CreateAttribute("trident:name", Sdf.ValueTypeNames.String).Set("Pipeline Main Line (Full Mode)")
    # Express belt — parallel at Y=+0.7. SILVER frame.
    build_conveyor(stage, "/World/AccumulationPipeline/ExpressLine",
                   x_start=5.8, x_end=19.4, y_center=+0.7,
                   z_top=0.7, width=1.0, mats=mats,
                   frame_mat_key="metal_silver",
                   belt_mat_key="conveyor_belt_express")

    # 7 gates at station_x positions, each spanning both belts.
    # Shifted east so the Accumulation belts no longer visually intrude into Raw Bucket.
    # Current one-shot catalog-first pipeline:
    #   PROFILE → MATERIALIZE → CATALOG → LINK → GRAPH → SEMANTIC → READY
    operation_specs = [
        (1, "PROFILE",  "object_schema_profile",   "asset_registry",   "trident.{ns}.trident_asset_registry",    "metal_bronze"),
        (2, "MATERIAL", "cardinality_materialize", "iceberg_table",    "trident.{ns}.*",                         "schema_bar"),
        (3, "CATALOG",  "catalog_tables_columns",  "catalog_metadata", "trident.{ns}.trident_catalog_tables",    "quality_bar"),
        (4, "LINK",     "asset_link_audit",        "link_audit",       "trident.{ns}.trident_asset_links",       "policy_tag"),
        (5, "GRAPH",    "redis_component_graph",   "component_graph",  "redis.trident:component_graph:{ns}",     "redis_card"),
        (6, "SEMANTIC", "milvus_semantic_index",   "semantic_index",   "milvus.trident_catalog",                "semantic_tag"),
        (7, "READY",    "dataset_ready_status",    "dataset_manifest", "trident.{ns}.trident_dataset_manifest",  "policy_tag"),
    ]
    for step_no, code_label, operation, output_kind, output_entity, mat_key in operation_specs:
        gx = station_x[step_no - 1]
        make_pipeline_operation_step(
            stage, f"/World/DataReadiness/ProcessFlow/Step_{step_no:02d}_{code_label}",
            (gx, 0.0, 0.0), mats, step_no=step_no, code_label=code_label, operation=operation,
            output_kind=output_kind, output_entity=output_entity, bar_mat_key=mat_key,
        )

    # Metadata station anchors (tiny floor anchors for live binding compat)
    cube(stage, "/World/Metadata/ExplainingStation",
         (station_x[5], 0.0, 0.04), (1.6, 3.0, 0.04), mats["concrete"],
         name="Explaining Metadata Station", entity_id="station.metadata.explaining",
         entity_type="metadata_station", stage_name="explaining")
    cube(stage, "/World/Metadata/SharingStation",
         (station_x[6], 0.0, 0.04), (1.6, 3.0, 0.04), mats["concrete"],
         name="Sharing Metadata Station", entity_id="station.metadata.sharing",
         entity_type="metadata_station", stage_name="sharing")
    cube(stage, "/World/AccumulationPipeline/ToLakehouseConveyor",
         (19.75, 0.0, 0.65), (0.05, 0.05, 0.05), mats["conveyor_belt"],
         name="To Lakehouse Conveyor (anchor)",
         entity_id="pipeline.to_lakehouse",
         entity_type="pipeline", stage_name="staging")

    # No convergence Y-bends here: the two Accumulation lines stay straight into
    # the Lakehouse west side so they do not clutter the view.

    # ===== Zone 4+5: Lakehouse unified (Y=11, 19 x 32 x 6) =====
    # Y range: 11-16=-5 ~ 11+16=+27. Labels at Y=-7.6 are visible south of warehouse.
    # Bottom half (Y: -5~+11) = TABLE STORE; Top half (Y: +11~+27) = STAGING
    lh_cx, lh_cy, lh_cz = 29.0, 11.0, 0.10
    lh_sx, lh_sy, lh_sz = 19.0, 32.0, 6.0
    cube(stage, "/World/Lakehouse/SilverLakehouse",
         (lh_cx, lh_cy, lh_cz),
         (lh_sx, lh_sy, 0.18), mats["concrete"],
         name="Silver Lakehouse", entity_id="lakehouse.silver",
         entity_type="storage_zone", stage_name="staging")
    # Staging 절반 바닥을 골드로 덮어씌움 (y=13.5~27.0, cy=20.25, sy=13.5)
    staging_cy = lh_cy + 9.25  # 11.0 + 9.25 = 20.25
    cube(stage, "/World/Lakehouse/StagingFloor",
         (lh_cx, staging_cy, lh_cz + 0.09),
         (lh_sx - 0.2, 13.5, 0.10), mats["metal_gold"])
    build_warehouse(stage, "/World/Lakehouse",
                    center=(lh_cx, lh_cy, lh_cz + 0.10),
                    size=(lh_sx, lh_sy, lh_sz),
                    wall_mat=mats["glass_lakehouse"], frame_mat=mats["steel_frame"],
                    left_gap=(-11.0, 2.0, 1.1),
                    right_gap=(+11.0, 2.0, 1.1))
    # Open floor plan — no internal divider between table zone and staging zone.
    # ===== TABLE STORE (lower half, Y: -4 ~ +10) =====
    # Tables are not drawn as a fixed furniture grid. Instead, Lakehouse slots
    # mirror Raw Bucket dataset slots: each raw namespace gets one Lakehouse
    # group, and only the actual generated tables for that namespace are shown.
    UsdGeom.Scope.Define(stage, "/World/Lakehouse/Tables")

    # Inventory crates — auto-generated from live twin-hub/stats-service (sync_scene_from_live.py)
    # Namespace scopes
    define_scope(stage, "/World/DataReadiness/Inventory/Icu_Ehr_Tabular_V1",
                 entity_id="inventory.namespace.icu_ehr_tabular_v1", entity_type="inventory_namespace",
                 namespace="icu_ehr_tabular_v1", zone="zone.lakehouse_inventory")
    define_scope(stage, "/World/DataReadiness/Inventory/Icu_Imaging_Mixed_V1",
                 entity_id="inventory.namespace.icu_imaging_mixed_v1", entity_type="inventory_namespace",
                 namespace="icu_imaging_mixed_v1", zone="zone.lakehouse_inventory")
    define_scope(stage, "/World/DataReadiness/Inventory/Icu_Notes_Metadata_V1",
                 entity_id="inventory.namespace.icu_notes_metadata_v1", entity_type="inventory_namespace",
                 namespace="icu_notes_metadata_v1", zone="zone.lakehouse_inventory")
    define_scope(stage, "/World/DataReadiness/Inventory/Icu_Sepsis_Cohort_V1",
                 entity_id="inventory.namespace.icu_sepsis_cohort_v1", entity_type="inventory_namespace",
                 namespace="icu_sepsis_cohort_v1", zone="zone.lakehouse_inventory")
    define_scope(stage, "/World/DataReadiness/Inventory/Icu_Waveform_Mixed_V1",
                 entity_id="inventory.namespace.icu_waveform_mixed_v1", entity_type="inventory_namespace",
                 namespace="icu_waveform_mixed_v1", zone="zone.lakehouse_inventory")

    inventory_specs = [
        ("Icu_Notes_Metadata_V1/Note_Manifest", "table.icu_notes_metadata_v1.note_manifest", "icu_notes_metadata_v1", "note_manifest",
         (21.8, -1.8000000000000007, 1.45), 16, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Notes_Metadata_V1/Dataset_Manifest", "table.icu_notes_metadata_v1.dataset_manifest", "icu_notes_metadata_v1", "dataset_manifest",
         (24.2, -1.8000000000000007, 1.45), 1, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Imaging_Mixed_V1/Radiology_Reports", "table.icu_imaging_mixed_v1.radiology_reports", "icu_imaging_mixed_v1", "radiology_reports",
         (26.6, -1.8000000000000007, 1.45), 2400, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Imaging_Mixed_V1/Image_Manifest", "table.icu_imaging_mixed_v1.image_manifest", "icu_imaging_mixed_v1", "image_manifest",
         (29.0, -1.8000000000000007, 1.45), 24, 0, 1.0, 0, True, True, True, "observed", "AI+HPDA"),
        ("Icu_Imaging_Mixed_V1/Dataset_Manifest", "table.icu_imaging_mixed_v1.dataset_manifest", "icu_imaging_mixed_v1", "dataset_manifest",
         (31.4, -1.8000000000000007, 1.45), 1, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Waveform_Mixed_V1/Waveform_Manifest", "table.icu_waveform_mixed_v1.waveform_manifest", "icu_waveform_mixed_v1", "waveform_manifest",
         (33.8, -1.8000000000000007, 1.45), 48, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Waveform_Mixed_V1/Dataset_Manifest", "table.icu_waveform_mixed_v1.dataset_manifest", "icu_waveform_mixed_v1", "dataset_manifest",
         (36.2, -1.8000000000000007, 1.45), 1, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Waveform_Mixed_V1/Patients", "table.icu_waveform_mixed_v1.patients", "icu_waveform_mixed_v1", "patients",
         (21.8, 0.5999999999999996, 1.45), 3000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Waveform_Mixed_V1/Icustays", "table.icu_waveform_mixed_v1.icustays", "icu_waveform_mixed_v1", "icustays",
         (24.2, 0.5999999999999996, 1.45), 5000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Waveform_Mixed_V1/Admissions", "table.icu_waveform_mixed_v1.admissions", "icu_waveform_mixed_v1", "admissions",
         (26.6, 0.5999999999999996, 1.45), 5000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Ehr_Tabular_V1/Dataset_Manifest", "table.icu_ehr_tabular_v1.dataset_manifest", "icu_ehr_tabular_v1", "dataset_manifest",
         (29.0, 0.5999999999999996, 1.45), 1, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Ehr_Tabular_V1/Vital_Events", "table.icu_ehr_tabular_v1.vital_events", "icu_ehr_tabular_v1", "vital_events",
         (31.4, 0.5999999999999996, 1.45), 700000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Ehr_Tabular_V1/Procedure_Events", "table.icu_ehr_tabular_v1.procedure_events", "icu_ehr_tabular_v1", "procedure_events",
         (33.8, 0.5999999999999996, 1.45), 60000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Ehr_Tabular_V1/Patients", "table.icu_ehr_tabular_v1.patients", "icu_ehr_tabular_v1", "patients",
         (36.2, 0.5999999999999996, 1.45), 12000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Ehr_Tabular_V1/Medication_Events", "table.icu_ehr_tabular_v1.medication_events", "icu_ehr_tabular_v1", "medication_events",
         (21.8, 3.0, 1.45), 120000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Ehr_Tabular_V1/Lab_Events", "table.icu_ehr_tabular_v1.lab_events", "icu_ehr_tabular_v1", "lab_events",
         (24.2, 3.0, 1.45), 360000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Ehr_Tabular_V1/Icustays", "table.icu_ehr_tabular_v1.icustays", "icu_ehr_tabular_v1", "icustays",
         (26.6, 3.0, 1.45), 22000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Ehr_Tabular_V1/Admissions", "table.icu_ehr_tabular_v1.admissions", "icu_ehr_tabular_v1", "admissions",
         (29.0, 3.0, 1.45), 22000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Sepsis_Segment_Manifest", "table.icu_sepsis_cohort_v1.sepsis_segment_manifest", "icu_sepsis_cohort_v1", "sepsis_segment_manifest",
         (31.4, 3.0, 1.45), 16, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Dataset_Manifest", "table.icu_sepsis_cohort_v1.dataset_manifest", "icu_sepsis_cohort_v1", "dataset_manifest",
         (33.8, 3.0, 1.45), 1, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Vasopressor_Events", "table.icu_sepsis_cohort_v1.vasopressor_events", "icu_sepsis_cohort_v1", "vasopressor_events",
         (36.2, 3.0, 1.45), 36000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Sofa_Scores", "table.icu_sepsis_cohort_v1.sofa_scores", "icu_sepsis_cohort_v1", "sofa_scores",
         (21.8, 5.4, 1.45), 72000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Sepsis_Cohort", "table.icu_sepsis_cohort_v1.sepsis_cohort", "icu_sepsis_cohort_v1", "sepsis_cohort",
         (24.2, 5.4, 1.45), 12000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Qsofa_Scores", "table.icu_sepsis_cohort_v1.qsofa_scores", "icu_sepsis_cohort_v1", "qsofa_scores",
         (26.6, 5.4, 1.45), 72000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Lactate_Results", "table.icu_sepsis_cohort_v1.lactate_results", "icu_sepsis_cohort_v1", "lactate_results",
         (29.0, 5.4, 1.45), 48000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Fluid_Boluses", "table.icu_sepsis_cohort_v1.fluid_boluses", "icu_sepsis_cohort_v1", "fluid_boluses",
         (31.4, 5.4, 1.45), 24000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Blood_Cultures", "table.icu_sepsis_cohort_v1.blood_cultures", "icu_sepsis_cohort_v1", "blood_cultures",
         (33.8, 5.4, 1.45), 24000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
        ("Icu_Sepsis_Cohort_V1/Antibiotic_Events", "table.icu_sepsis_cohort_v1.antibiotic_events", "icu_sepsis_cohort_v1", "antibiotic_events",
         (36.2, 5.4, 1.45), 36000, 0, 1.0, 0, False, False, True, "observed", "HPDA"),
    ]
    live_inventory_specs = _fetch_lakehouse_inventory_specs(max_tables=64)
    if live_inventory_specs:
        inventory_specs = [
            (s["rel_path"], s["entity_id"], s["namespace"], s["component"],
             (0.0, 0.0, 0.0), s["row_count"], s["object_count"],
             s["quality_score"], s["access_frequency"], s["semantic"],
             s["location"], s["policy"], s["freshness"], s["workload_fit"])
            for s in live_inventory_specs
        ]

    def _table_role(component: str) -> str:
        token = component.lower()
        metadata_tokens = ("manifest", "metadata", "catalog", "asset", "schema", "lineage", "link", "index")
        return "metadata" if any(t in token for t in metadata_tokens) else "data"

    def _safe_name(value: str) -> str:
        return value.replace("-", "_").replace(".", "_").title()

    def _short_table_label(component: str) -> str:
        token = component.upper().replace("TRIDENT_", "").replace("_", " ")
        aliases = {
            "DATASET MANIFEST": "DS",
            "NOTE MANIFEST": "NOTE",
            "IMAGE MANIFEST": "IMG",
            "WAVEFORM MANIFEST": "WAVE",
            "RADIOLOGY REPORTS": "RAD",
            "VITAL EVENTS": "VITAL",
            "PROCEDURE EVENTS": "PROC",
            "MEDICATION EVENTS": "MED",
            "LAB EVENTS": "LAB",
            "SEPSIS SEGMENT MANIFEST": "SEPSIS",
            "VASOPRESSOR EVENTS": "VASO",
            "SOFA SCORES": "SOFA",
            "QSOFA SCORES": "QSOFA",
            "LACTATE RESULTS": "LACT",
            "FLUID BOLUSES": "FLUID",
            "BLOOD CULTURES": "CULT",
            "ANTIBIOTIC EVENTS": "ABX",
        }
        if token in aliases:
            return aliases[token]
        return token.split()[0][:6] if token.split() else token[:6]

    def _slot_grid_center(slot_index: int) -> tuple[float, float]:
        # Fallback only for inventory namespaces that do not have a Raw Bucket slot.
        # Normal Lakehouse placement mirrors the Raw Bucket 3x3 namespace cells.
        cols = 8
        col = slot_index % cols
        row = slot_index // cols
        return (lh_cx - 7.6 + col * (ZONE_W + ZONE_GAP_X), lh_cy - 13.7 + row * (ZONE_TOTAL_D + 0.20))

    def _lakehouse_slot_from_raw(ns: str, fallback_index: int) -> tuple[float, float, float]:
        raw_center = raw_slot_centers.get(ns)
        if raw_center is None:
            gx, gy_boxes = _slot_grid_center(fallback_index)
            return gx, gy_boxes, gy_boxes - LABEL_H / 2
        # Preserve the exact 3x3 Raw Bucket cell footprint, translated into Lakehouse.
        gx = raw_center[0] + (lh_cx - raw_cx)
        gy_boxes = raw_center[1]
        gy_slot = gy_boxes - LABEL_H / 2
        return gx, gy_boxes, gy_slot

    grouped_inventory: dict[str, list[tuple]] = {}
    for spec in inventory_specs:
        grouped_inventory.setdefault(spec[2], []).append(spec)

    ordered_namespaces = [ns for ns in RAW_NAMESPACES if ns in grouped_inventory]
    ordered_namespaces.extend(ns for ns in grouped_inventory if ns not in ordered_namespaces)

    for group_idx, ns in enumerate(ordered_namespaces):
        specs = grouped_inventory[ns]
        gx, gy_boxes, gy_slot = _lakehouse_slot_from_raw(ns, group_idx)
        safe_ns = _safe_name(ns)
        slot_w = ZONE_W
        slot_d = ZONE_TOTAL_D
        cube(stage, f"/World/Lakehouse/Tables/{safe_ns}/SlotBase",
             (gx, gy_slot, 0.18), (slot_w, slot_d, 0.08), mats["lakehouse_slot_base"],
             name=f"{ns} lakehouse slot", entity_id=f"lakehouse.slot.{ns}",
             entity_type="lakehouse_dataset_slot", stage_name="lakehouse_inventory")
        # Thin dividers make the Lakehouse cells read like Raw Bucket cells.
        cube(stage, f"/World/Lakehouse/Tables/{safe_ns}/DividerS",
             (gx, gy_slot - slot_d / 2, 0.24), (slot_w, 0.035, 0.12), mats["steel_frame"])
        cube(stage, f"/World/Lakehouse/Tables/{safe_ns}/DividerN",
             (gx, gy_slot + slot_d / 2, 0.24), (slot_w, 0.035, 0.12), mats["steel_frame"])
        cube(stage, f"/World/Lakehouse/Tables/{safe_ns}/DividerW",
             (gx - slot_w / 2, gy_slot, 0.24), (0.035, slot_d, 0.12), mats["steel_frame"])
        cube(stage, f"/World/Lakehouse/Tables/{safe_ns}/DividerE",
             (gx + slot_w / 2, gy_slot, 0.24), (0.035, slot_d, 0.12), mats["steel_frame"])
        render_text(stage, f"/World/Lakehouse/Tables/{safe_ns}/Label",
                    ns.upper().replace("_", " "), (gx, gy_slot - slot_d / 2 + 0.16, 0.28),
                    mats, pixel=0.0060, height_z=0.010, color_key="black_panel")
        # A low tabletop supports the per-table crates. The tabletop footprint stays
        # inside the Raw Bucket-sized namespace slot.
        table_top_z = 0.38
        cube(stage, f"/World/Lakehouse/Tables/{safe_ns}/TableTop",
             (gx, gy_boxes, table_top_z), (slot_w * 0.90, ZONE_D * 0.66, 0.08), mats["table_top"])
        for lx, ly, lname in [
            (-1, -1, "SW"), (-1, +1, "NW"), (+1, -1, "SE"), (+1, +1, "NE"),
        ]:
            cube(stage, f"/World/Lakehouse/Tables/{safe_ns}/Leg_{lname}",
                 (gx + lx * slot_w * 0.36, gy_boxes + ly * ZONE_D * 0.24, 0.20),
                 (0.05, 0.05, 0.34), mats["table_leg"])
        cols = COLS
        slots_per_layer = COLS * ROWS
        box_scale = (0.26, 0.20, 0.16)
        zone_x0 = gx - ZONE_W / 2
        zone_y0 = gy_boxes - ZONE_D / 2
        for idx, (rel_path, eid, _ns, comp, _pos, rows, objects, quality, access, semantic, location, policy, freshness, fit) in enumerate(specs):
            slot = idx % slots_per_layer
            layer = idx // slots_per_layer
            col = slot % cols
            row = slot // cols
            role = _table_role(comp)
            tx = zone_x0 + col * CELL + CELL / 2
            ty = zone_y0 + row * CELL + CELL / 2
            tz = 0.54 + layer * 0.23
            make_readiness_table_crate(
                stage, f"/World/DataReadiness/Inventory/{rel_path}", (tx, ty, tz),
                box_scale, mats, entity_id=eid, namespace=_ns,
                component=comp, row_count=rows, object_count=objects,
                quality_score=quality, access_frequency=access, semantic=semantic,
                location=location, policy=policy, freshness=freshness, workload_fit=fit,
                table_role=role,
            )
            render_text(stage, f"/World/Lakehouse/Tables/{safe_ns}/TableLabel_{idx:02d}",
                        _short_table_label(comp), (tx, ty, tz + 0.115), mats,
                        pixel=0.0042, height_z=0.006, color_key="black_panel")
    # ===== Staging zone (north half of unified Lakehouse, Y: +13~+26 world coords) =====
    # Empty showcase tables for future frequently used datasets. No static boxes are
    # placed here yet; live/curated bundles can be added later.
    UsdGeom.Scope.Define(stage, "/World/Showcase/Displays")
    UsdGeom.Scope.Define(stage, "/World/Lakehouse/Staging")
    staging_table_ys = [16.0, 20.0, 24.0]
    for si, scy in enumerate(staging_table_ys, start=1):
        rp = f"/World/Lakehouse/Staging/DisplayTable_{si}"
        UsdGeom.Scope.Define(stage, rp)
        table_cx = lh_cx
        table_w = 14.5
        table_d = 1.15
        table_top_z = 0.78
        leg_h = table_top_z - 0.08
        cube(stage, f"{rp}/Top",
             (table_cx, scy, table_top_z), (table_w, table_d, 0.10), mats["table_top"],
             name=f"Staging display table {si}", entity_id=f"staging.display_table.{si}",
             entity_type="staging_display_table", stage_name="staging")
        for lx, ly, lname in [
            (-1, -1, "SW"), (-1, +1, "NW"), (+1, -1, "SE"), (+1, +1, "NE"),
        ]:
            cube(stage, f"{rp}/Leg_{lname}",
                 (table_cx + lx * (table_w / 2 - 0.25), scy + ly * (table_d / 2 - 0.15), leg_h / 2),
                 (0.10, 0.10, leg_h), mats["table_leg"])
        cube(stage, f"{rp}/BackRail",
             (table_cx, scy + table_d / 2 - 0.05, table_top_z + 0.12),
             (table_w * 0.96, 0.08, 0.14), mats["metal_gold"])
        render_text(stage, f"{rp}/Label",
                    "FREQUENT DATASETS", (table_cx, scy - table_d / 2 + 0.10, table_top_z + 0.08),
                    mats, pixel=0.022, height_z=0.010, color_key="black_panel")

    # Keep the ReadyBundles scope as a semantic target, but leave it empty until
    # real frequently-used dataset selections are available.
    # Lakehouse -> Showcase promotion belt removed; zones are now unified as LAKEHOUSE ZONE.

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
    make_search_highlight(stage, "/World/DataReadiness/SearchSelection/Intent_Camera_Lidar",
                          (44.0, 10.4, 0.08), (7.2, 6.4, 0.04), mats,
                          entity_id="search.intent.camera_lidar",
                          query="camera + lidar", candidate_count=4)
    cube(stage, "/World/DataReadiness/SearchSelection/ReadinessComparePanel",
         (44.0, 13.6, 2.6), (2.8, 0.08, 0.9), mats["monitor_screen"],
         name="Readiness Compare Panel", entity_id="search.panel.readiness",
         entity_type="search_panel", stage_name="selection")
    set_trident_attrs(stage.GetPrimAtPath("/World/DataReadiness/SearchSelection/ReadinessComparePanel"),
                      query="camera + lidar", compares="quality,policy,semantic,location,cache",
                      explains_missing_metadata=True)

    # Search Zone starts with one static scene user so the zone is visible before Live starts.
    # The Isaac extension replaces /World/Avatars/ActiveUser from viewer_state commands when Portal is open.
    UsdGeom.Scope.Define(stage, "/World/Avatars")
    define_scope(stage, "/World/Avatars/SceneUser",
                 entity_id="viewer.scene.default", entity_type="active_viewer",
                 zone="zone.search", role="researcher")
    cube(stage, "/World/Avatars/SceneUser/Body", (44.0, 8.0, 0.82),
         (0.24, 0.18, 0.70), mats["role_researcher"])
    sphere(stage, "/World/Avatars/SceneUser/Head", (44.0, 8.0, 1.55), 0.18, mats["skin_tone"])
    cube(stage, "/World/Avatars/SceneUser/RoleBadge", (44.0, 8.0, 1.90),
         (0.34, 0.34, 0.08), mats["role_operator"])
    render_text(stage, "/World/Avatars/SceneUser/Label",
                "USER", (44.0, 7.55, 0.035), mats, pixel=0.030, height_z=0.012, color_key="black_panel")

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
    # No static boxes on the Delivery table. Packages appear only after Send to Delivery.

    # Canonical workload delivery packages generated from selected ready bundles.

    # Incoming rails: Lakehouse and Staging feed the consolidation table, but no static boxes.
    # Live packages appear only after Send to Delivery.
    big_t_west = big_table_cx - big_table_w / 2
    lakehouse_east = lh_cx + lh_sx / 2
    search_south_y = 2.2  # below Search Zone pad (y min ~= 3)
    search_north_y = 18.2 # above Search Zone pad (y max ~= 17)
    detour_x = big_t_west + 0.25
    build_conveyor(stage, "/World/DeliveryYard/InBelt_Lakehouse",
                   x_start=lakehouse_east + 0.2, x_end=detour_x, y_center=search_south_y,
                   z_top=0.7, width=0.72, mats=mats,
                   frame_mat_key="metal_silver")
    build_conveyor_Y(stage, "/World/DeliveryYard/InBelt_Lakehouse_ToTable",
                     y_start=search_south_y, y_end=6.4, x_center=detour_x,
                     z_top=0.7, width=0.72, mats=mats,
                     frame_mat_key="metal_silver")
    build_conveyor(stage, "/World/DeliveryYard/InBelt_Staging",
                   x_start=lakehouse_east + 0.2, x_end=detour_x, y_center=search_north_y,
                   z_top=0.7, width=0.72, mats=mats,
                   frame_mat_key="metal_gold",
                   belt_mat_key="conveyor_belt_express")
    build_conveyor_Y(stage, "/World/DeliveryYard/InBelt_Staging_ToTable",
                     y_start=13.6, y_end=search_north_y, x_center=detour_x,
                     z_top=0.7, width=0.72, mats=mats,
                     frame_mat_key="metal_gold",
                     belt_mat_key="conveyor_belt_express")

    # ---- 3 STRAIGHT outgoing belts: big table east edge -> each truck (no bends) ----
    # Big Table now wide enough in Y to cover all 3 truck Y lanes, so each belt is
    # a single straight east-going segment from table east edge to truck rear.
    big_t_east = big_table_cx + big_table_w / 2  # +54
    for nm, dy in zip(dock_names, dock_ys):
        build_conveyor(stage, f"/World/DeliveryYard/OutBelt_{nm}",
                       x_start=big_t_east, x_end=truck_rear_x - 0.5, y_center=dy,
                       z_top=0.7, width=0.9, mats=mats,
                       frame_mat_key="conveyor_promotion")
        # No static package box here; live delivery animation creates it on demand.

    # ---- Trucks parked east (cab +X, open rear at truck_rear_x) ----
    build_ai_truck(stage, "/World/DeliveryYard/Vehicle_AI",
                   truck_rear_x, dock_ys[0], mats)
    build_hpc_van(stage, "/World/DeliveryYard/Vehicle_HPC",
                  truck_rear_x, dock_ys[1], mats)
    build_hpda_van(stage, "/World/DeliveryYard/Vehicle_HPDA",
                   truck_rear_x, dock_ys[2], mats)
    # Painted truck labels ON TOP of each truck body, centered, flat
    # AI: body_len=3.8, body_h=2.2  -> body_cx=63.9, top_z=3.05
    # HPC: body_len=3.4, body_h=2.0 -> body_cx=63.7, top_z=2.85
    # HPDA: body_len=3.6, body_h=2.0 -> body_cx=63.8, top_z=2.85
    render_text(stage, "/World/DeliveryYard/Labels/AI",
                "AI",   (63.9, dock_ys[0], 3.06), mats, pixel=0.10)
    render_text(stage, "/World/DeliveryYard/Labels/HPC",
                "HPC",  (63.7, dock_ys[1], 2.86), mats, pixel=0.08)
    render_text(stage, "/World/DeliveryYard/Labels/HPDA",
                "HPDA", (63.8, dock_ys[2], 2.86), mats, pixel=0.07)

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

    # ===== Top-down (90deg) per-zone capture cameras =====
    # Position above each zone center, looking straight down. Default camera
    # orientation is -Z forward / +Y up, so no rotation needed: standing at
    # (cx, cy, h) with no rotation gives a top-down view with +X right, +Y up.
    top_cams = [
        ("Top_Overview",      ( 15,  +7, 95), 14),
        ("Top_Ingest",        (-22,   0, 22), 22),
        ("Top_RawBucket",     ( -4,  -1, 13), 45),
        ("zone_02_raw_bucket",( -4,  -1, 13), 45),
        ("Top_Accumulation",  (+12,   0, 18), 24),
        ("Top_Lakehouse",     (+29,  -1, 13), 45),
        ("zone_04_lakehouse", (+29,  -1, 13), 45),
        ("Top_Staging",       (+29, +21, 22), 28),
        ("zone_04_staging",   (+29, +21, 22), 28),
        ("Top_Search",        (+44, +10, 18), 26),
        ("Top_Delivery",      (+59, +10, 22), 26),
        ("Top_Tower",         (-22, +25, 22), 22),
    ]
    UsdGeom.Scope.Define(stage, "/World/Cameras")
    for name, pos, focal in top_cams:
        tcam = UsdGeom.Camera.Define(stage, f"/World/Cameras/{name}")
        UsdGeom.XformCommonAPI(tcam).SetTranslate(Gf.Vec3d(*pos))
        tcam.CreateFocalLengthAttr(focal)

    # ===== Oblique (45deg) portal/demo cameras =====
    # Portal camera switching uses these as the primary zone presets. They are
    # persisted in the generated USD instead of being created only by
    # capture_overview.py so the live Isaac stream can switch to them.
    def add_look_at_camera(usd_path: str, translate, look_at, focal_mm: float) -> None:
        cam = UsdGeom.Camera.Define(stage, usd_path)
        eye = Gf.Vec3d(*translate)
        center = Gf.Vec3d(*look_at)
        up = Gf.Vec3d(0, 1, 0)
        fwd = (center - eye).GetNormalized()
        right = Gf.Cross(fwd, up).GetNormalized()
        up_corrected = Gf.Cross(right, fwd).GetNormalized()
        mat = Gf.Matrix4d(
            right[0],        right[1],        right[2],        0,
            up_corrected[0], up_corrected[1], up_corrected[2], 0,
            -fwd[0],         -fwd[1],         -fwd[2],         0,
            eye[0],          eye[1],          eye[2],          1,
        )
        xf = UsdGeom.Xformable(cam)
        xf.ClearXformOpOrder()
        op = xf.AddXformOp(UsdGeom.XformOp.TypeTransform, UsdGeom.XformOp.PrecisionDouble)
        op.Set(mat)
        cam.CreateFocalLengthAttr(focal_mm)
        cam.CreateClippingRangeAttr(Gf.Vec2f(0.1, 2000.0))

    oblique_cams = [
        ("/World/Cameras/Overview_Top45",       (25.0, -65.0, 65.0), (25.0, 10.0, 0.0), 12.0),
        ("/World/Cameras/zone_01_truck_yard",  (-22.0, -22.0, 22.0), (-22.0,  0.0, 1.5), 18.0),
        ("/World/Cameras/zone_03_accumulation",( 12.0, -12.0, 14.0), ( 12.0,  0.0, 1.2), 24.0),
        ("/World/Cameras/zone_05_search",      ( 44.0,  -2.0, 13.0), ( 44.0, 10.0, 1.2), 24.0),
        ("/World/Cameras/zone_06_delivery",    ( 59.0,  -5.0, 17.0), ( 59.0, 10.0, 1.2), 24.0),
        ("/World/Cameras/zone_07_tower",       (-22.0,  10.0, 15.0), (-22.0, 25.0, 1.2), 24.0),
    ]
    for usd_path, translate, look_at, focal in oblique_cams:
        add_look_at_camera(usd_path, translate, look_at, focal)

    # ===== Existing oblique / cinematic cameras =====
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
