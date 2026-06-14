"""stats-service 라이브 데이터를 기반으로 USD entity_id를 정렬한다.

twin-hub가 생성하는 entity_id(table.<namespace>.<table>)와
USD 씬의 trident:entity_id가 일치하도록 create_scene.py를 재생성한다.

사용법:
    # 기본 (fixture 모드 — stats-service 없이 구조만 검증)
    python3 scripts/sync_scene_from_live.py

    # 라이브 모드
    TRIDENT_STATS_BASE_URL=http://10.234.33.83 \
    TRIDENT_STATS_TOKEN=<token> \
    python3 scripts/sync_scene_from_live.py

    # Keycloak 자동 갱신 모드
    TRIDENT_STATS_BASE_URL=http://10.234.33.83 \
    TRIDENT_KC_URL=http://10.38.38.220:8080/realms/trident/protocol/openid-connect/token \
    TRIDENT_KC_CLIENT_ID=trident-baseline-runner \
    TRIDENT_KC_CLIENT_SECRET=<secret> \
    python3 scripts/sync_scene_from_live.py

출력:
    scripts/create_scene.py 내의 inventory_specs 블록을 라이브 데이터 기반으로 교체.
    USD 씬은 Isaac Sim에서 별도로 재생성 필요.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SCENE_SCRIPT = REPO_ROOT / "scripts" / "create_scene.py"

STATS_BASE = os.getenv("TRIDENT_STATS_BASE_URL", "").rstrip("/")
TWIN_HUB_URL = os.getenv("TWIN_HUB_URL", "").rstrip("/")
STATIC_TOKEN = os.getenv("TRIDENT_STATS_TOKEN", "")
KC_URL = os.getenv("TRIDENT_KC_URL", "")
KC_CLIENT_ID = os.getenv("TRIDENT_KC_CLIENT_ID", "trident-baseline-runner")
KC_CLIENT_SECRET = os.getenv("TRIDENT_KC_CLIENT_SECRET", "")
HTTP_TIMEOUT = float(os.getenv("TRIDENT_TWIN_HTTP_TIMEOUT", "20"))


# ============================================================================
# 토큰 관리 (twin-hub/_TokenCache와 동일 로직)
# ============================================================================
class _TokenCache:
    def __init__(self) -> None:
        self._token = STATIC_TOKEN
        self._expires_at = 0.0

    def get(self) -> str:
        if self._token and not KC_URL:
            return self._token
        if time.monotonic() < self._expires_at - 60:
            return self._token
        return self._refresh()

    def _refresh(self) -> str:
        if not KC_URL or not KC_CLIENT_SECRET:
            return self._token
        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": KC_CLIENT_ID,
            "client_secret": KC_CLIENT_SECRET,
        }).encode()
        req = urllib.request.Request(
            KC_URL, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            payload = json.loads(r.read().decode())
        self._token = payload["access_token"]
        self._expires_at = time.monotonic() + int(payload.get("expires_in", 3600))
        print(f"[token] 갱신 완료, expires_in={payload.get('expires_in')}s")
        return self._token


_token_cache = _TokenCache()


def _fetch(path: str) -> Any:
    url = f"{STATS_BASE}{path}"
    req = urllib.request.Request(url)
    token = _token_cache.get()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f"[error] {path} → HTTP {e.code}")
        raise
    except Exception as e:
        print(f"[error] {path} → {e}")
        raise



def fetch_inventory_specs_from_twin_hub(max_tables: int = 32) -> list[dict]:
    """Read live iceberg_table entities from deployed twin-hub; no Keycloak secret needed."""
    if not TWIN_HUB_URL:
        return []
    print(f"[fetch] {TWIN_HUB_URL}/api/twin/entities")
    req = urllib.request.Request(f"{TWIN_HUB_URL}/api/twin/entities")
    with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT) as r:
        payload = json.loads(r.read().decode())
    tables = [e for e in payload.get("entities", []) if e.get("type") == "iceberg_table"]
    specs = []
    seen: set[str] = set()
    lh_cx = 29.0
    lh_cy = 11.0
    xs = [lh_cx - 7.2, lh_cx - 4.8, lh_cx - 2.4, lh_cx, lh_cx + 2.4, lh_cx + 4.8, lh_cx + 7.2]
    ys = [lh_cy - 12.8, lh_cy - 10.4, lh_cy - 8.0, lh_cy - 5.6]
    for e in tables:
        entity_id = str(e.get("id") or "").lower()
        parts = entity_id.split(".")
        ns = str(e.get("namespace") or (parts[1] if len(parts) >= 3 else "default"))
        # component can be a coarse type/namespace in older hub payloads; the
        # canonical table name is the last segment of table.<namespace>.<table>.
        table = str((parts[2] if len(parts) >= 3 else "") or e.get("table") or e.get("name") or e.get("component") or "unknown")
        entity_id = entity_id or f"table.{ns}.{table}".lower()
        rel_path = f"{ns.title()}/{table.title()}".replace("-", "_").replace(".", "_")
        if rel_path in seen:
            continue
        seen.add(rel_path)
        idx = len(specs)
        if idx >= min(max_tables, len(xs) * len(ys)):
            break
        col = idx % len(xs)
        row_i = idx // len(xs)
        readiness = float(e.get("readiness_score") or e.get("quality_score") or 0.85)
        specs.append({
            "rel_path": rel_path,
            "entity_id": entity_id,
            "namespace": ns,
            "component": table,
            "pos": (xs[col], ys[row_i], 1.45),
            "row_count": int(e.get("row_count") or 0),
            "object_count": int(e.get("object_count") or e.get("total_assets") or 0),
            "quality_score": round(max(0.0, min(1.0, readiness)), 2),
            "access_frequency": int(e.get("access_frequency") or 0),
            "semantic": e.get("semantic_ready") if isinstance(e.get("semantic_ready"), bool) else True,
            "location": e.get("location_ready") if isinstance(e.get("location_ready"), bool) else True,
            "policy": e.get("policy_ready") if isinstance(e.get("policy_ready"), bool) else True,
            "freshness": str(e.get("freshness") or "live"),
            "workload_fit": str(e.get("workload_fit") or _workload_fit(table, ns)),
        })
    print(f"[fetch] twin-hub 테이블 {len(specs)}개 수집 완료")
    return specs

# ============================================================================
# stats-service 데이터 → inventory_specs 변환
# ============================================================================
def _split_table_name(table_full_name: str) -> tuple[str, str, str]:
    parts = [p.strip('"') for p in table_full_name.split(".") if p]
    if len(parts) >= 3:
        return parts[-3], parts[-2], parts[-1]
    if len(parts) == 2:
        return "trident", parts[0], parts[1]
    return "trident", "default", table_full_name or "unknown"


def _readiness(row: dict) -> float:
    integrity = row.get("integrity_pct")
    if integrity is not None:
        try:
            return round(max(0.0, min(1.0, float(integrity) / 100.0)), 2)
        except Exception:
            pass
    score = 0.35
    if row.get("row_count"):
        score += 0.20
    if row.get("nessie_commit"):
        score += 0.15
    if row.get("tags"):
        score += 0.15
    return round(min(score, 0.95), 2)


def _workload_fit(table_name: str, namespace: str) -> str:
    name = (table_name + namespace).lower()
    if any(k in name for k in ["camera", "image", "frame"]):
        return "AI+HPDA"
    if any(k in name for k in ["lidar", "point", "track"]):
        return "AI+HPC"
    if any(k in name for k in ["gps", "trajectory"]):
        return "HPC+HPDA"
    if any(k in name for k in ["weather", "grid"]):
        return "HPDA"
    return "AI+HPDA"


def fetch_inventory_specs(max_tables: int = 28) -> list[dict]:
    """stats-service에서 테이블 목록을 읽어 inventory_spec 딕셔너리 리스트 반환."""
    print(f"[fetch] {STATS_BASE}/api/v1/catalog/datasets")
    payload = _fetch("/api/v1/catalog/datasets?limit=100")
    datasets = payload.get("datasets", [])

    # overview에서 integrity 보완
    try:
        overview = _fetch("/api/v1/catalog/overview")
        by_name = {str(d.get("table_full_name")): d for d in overview.get("datasets", [])}
    except Exception:
        by_name = {}

    specs = []
    seen_paths: set[str] = set()
    for row in datasets:
        table_full_name = str(row.get("table_full_name") or "")
        if not table_full_name:
            continue
        _, namespace, table = _split_table_name(table_full_name)
        entity_id = f"table.{namespace}.{table}".lower()

        # overview 데이터 병합
        merged = dict(by_name.get(table_full_name, {}))
        merged.update(row)

        quality = _readiness(merged)
        tags = merged.get("tags") or []
        semantic = bool(tags) or True
        location = True
        policy = merged.get("sensitivity") not in {"restricted", "private"}
        freshness = "fresh" if merged.get("nessie_commit") else "observed"
        fit = _workload_fit(table, namespace)

        # USD 씬 내 배치 위치 — create_scene.py의 lh_cx=29 기준
        # 최대 max_tables개, 4열 배치
        idx = len(specs)
        lh_cx = 29.0
        lh_cy = 11.0
        xs = [lh_cx - 7.2, lh_cx - 4.8, lh_cx - 2.4, lh_cx, lh_cx + 2.4, lh_cx + 4.8, lh_cx + 7.2]
        col = idx % len(xs)
        row_i = idx // len(xs)
        ys_base = [lh_cy - 12.8, lh_cy - 10.4, lh_cy - 8.0, lh_cy - 5.6]
        if row_i >= len(ys_base):
            break
        pos = (xs[col], ys_base[row_i], 1.45)

        rel_path = f"{namespace.title()}/{table.title()}"
        # USD 경로에 특수문자 금지
        rel_path = rel_path.replace("-", "_").replace(".", "_")

        specs.append({
            "rel_path": rel_path,
            "entity_id": entity_id,
            "namespace": namespace,
            "component": table,
            "pos": pos,
            "row_count": int(merged.get("row_count") or 0),
            "object_count": int(merged.get("s3_file_count") or merged.get("index_row_count") or 0),
            "quality_score": quality,
            "access_frequency": 0,
            "semantic": semantic,
            "location": location,
            "policy": policy,
            "freshness": freshness,
            "workload_fit": fit,
        })
        seen_paths.add(rel_path)
        if len(specs) >= max_tables:
            break

    print(f"[fetch] 테이블 {len(specs)}개 수집 완료")
    return specs


# ============================================================================
# create_scene.py inventory_specs 블록 교체
# ============================================================================
BLOCK_START_CANDIDATES = ("    # Inventory crates", "    # Namespace scope anchors")
BLOCK_END = "    # ===== Staging zone"


def specs_to_python(specs: list[dict]) -> str:
    """inventory_specs 리스트를 create_scene.py 호환 Python 코드 블록으로 변환."""
    lines = [
        "    # Inventory crates — auto-generated from live twin-hub/stats-service (sync_scene_from_live.py)",
        "    # Namespace scopes",
    ]
    # namespace 스코프 정의
    namespaces = sorted({s["namespace"] for s in specs})
    for ns in namespaces:
        safe_ns = ns.title().replace("-", "_").replace(".", "_")
        lines.append(
            f"    define_scope(stage, \"/World/DataReadiness/Inventory/{safe_ns}\","
        )
        lines.append(
            f"                 entity_id=\"inventory.namespace.{ns}\","
            f" entity_type=\"inventory_namespace\","
        )
        lines.append(
            f"                 namespace=\"{ns}\", zone=\"zone.lakehouse_inventory\")"
        )

    lines.append("")
    lines.append("    inventory_specs = [")
    for s in specs:
        pos_str = f"({s['pos'][0]}, {s['pos'][1]}, {s['pos'][2]})"
        lines.append(f"        (\"{s['rel_path']}\", \"{s['entity_id']}\","
                     f" \"{s['namespace']}\", \"{s['component']}\",")
        lines.append(f"         {pos_str},"
                     f" {s['row_count']}, {s['object_count']},"
                     f" {s['quality_score']}, {s['access_frequency']},"
                     f" {s['semantic']}, {s['location']}, {s['policy']},"
                     f" \"{s['freshness']}\", \"{s['workload_fit']}\"),")
    lines.append("    ]")
    lines.append(
        "    for rel_path, eid, ns, comp, pos, rows, objects, quality, access,"
        " semantic, location, policy, freshness, fit in inventory_specs:"
    )
    lines.append("        make_readiness_table_crate(")
    lines.append(
        "            stage, f\"/World/DataReadiness/Inventory/{rel_path}\", pos,"
    )
    lines.append(
        "            (0.82, 0.58, 0.48), mats, entity_id=eid, namespace=ns,"
    )
    lines.append(
        "            component=comp, row_count=rows, object_count=objects,"
    )
    lines.append(
        "            quality_score=quality, access_frequency=access, semantic=semantic,"
    )
    lines.append(
        "            location=location, policy=policy, freshness=freshness, workload_fit=fit,"
    )
    lines.append("        )")
    return "\n".join(lines)


def patch_create_scene(specs: list[dict]) -> None:
    """create_scene.py의 inventory 블록을 라이브 데이터 기반으로 교체."""
    src = SCENE_SCRIPT.read_text(encoding="utf-8")
    lines = src.splitlines()

    # BLOCK_START ~ BLOCK_END 직전 사이를 찾아 교체. First run may only
    # have legacy namespace anchors; subsequent runs have the generated marker.
    start_idx = end_idx = None
    for i, line in enumerate(lines):
        if start_idx is None and any(marker in line for marker in BLOCK_START_CANDIDATES):
            start_idx = i
        if start_idx is not None and BLOCK_END in line:
            end_idx = i
            break

    if start_idx is None or end_idx is None:
        print("[warn] create_scene.py에서 inventory 블록을 찾지 못했습니다.")
        print(f"       BLOCK_START_CANDIDATES: {BLOCK_START_CANDIDATES!r}")
        print(f"       BLOCK_END:   {BLOCK_END!r}")
        return

    new_block = specs_to_python(specs).splitlines()
    patched = lines[:start_idx] + new_block + lines[end_idx:]
    SCENE_SCRIPT.write_text("\n".join(patched) + "\n", encoding="utf-8")
    print(f"[patch] create_scene.py 교체 완료 ({len(specs)}개 테이블, "
          f"라인 {start_idx}~{end_idx})")


# ============================================================================
# fixture 폴백 (stats-service 없을 때 구조 검증용)
# ============================================================================
FIXTURE_SPECS: list[dict] = [
    {
        "rel_path": "Autonomous_Test/Sensor_Frames",
        "entity_id": "table.autonomous_test.sensor_frames",
        "namespace": "autonomous_test", "component": "sensor_frames",
        "pos": (22.5, -2.0, 1.45),
        "row_count": 540000, "object_count": 380, "quality_score": 0.88,
        "access_frequency": 12, "semantic": True, "location": True,
        "policy": True, "freshness": "fresh", "workload_fit": "AI+HPDA",
    },
    {
        "rel_path": "Autonomous_Test/Lidar_Points",
        "entity_id": "table.autonomous_test.lidar_points",
        "namespace": "autonomous_test", "component": "lidar_points",
        "pos": (26.5, -2.0, 1.45),
        "row_count": 8300000, "object_count": 210, "quality_score": 0.84,
        "access_frequency": 8, "semantic": True, "location": True,
        "policy": True, "freshness": "fresh", "workload_fit": "AI+HPC",
    },
    {
        "rel_path": "Autonomous_Test/Gps_Trajectory",
        "entity_id": "table.autonomous_test.gps_trajectory",
        "namespace": "autonomous_test", "component": "gps_trajectory",
        "pos": (31.5, -2.0, 1.45),
        "row_count": 2100000, "object_count": 92, "quality_score": 0.79,
        "access_frequency": 5, "semantic": True, "location": True,
        "policy": True, "freshness": "warm", "workload_fit": "HPC+HPDA",
    },
    {
        "rel_path": "Autonomous_Weather/Weather_Grid",
        "entity_id": "table.autonomous_weather.weather_grid",
        "namespace": "autonomous_weather", "component": "weather_grid",
        "pos": (22.5, 1.5, 1.45),
        "row_count": 980000, "object_count": 36, "quality_score": 0.72,
        "access_frequency": 3, "semantic": False, "location": True,
        "policy": True, "freshness": "stale", "workload_fit": "HPDA",
    },
    {
        "rel_path": "Autonomous_Weather/Radar_Sweep",
        "entity_id": "table.autonomous_weather.radar_sweep",
        "namespace": "autonomous_weather", "component": "radar_sweep",
        "pos": (26.5, 1.5, 1.45),
        "row_count": 450000, "object_count": 18, "quality_score": 0.68,
        "access_frequency": 2, "semantic": False, "location": True,
        "policy": True, "freshness": "stale", "workload_fit": "HPDA",
    },
]


def main() -> None:
    if TWIN_HUB_URL:
        print(f"[mode] twin-hub live — {TWIN_HUB_URL}")
        try:
            specs = fetch_inventory_specs_from_twin_hub(max_tables=28)
        except Exception as e:
            print(f"[abort] twin-hub 오류: {e}")
            print("[abort] TWIN_HUB_URL live 모드에서는 fixture로 scene을 덮어쓰지 않습니다.")
            sys.exit(1)
    elif STATS_BASE:
        print(f"[mode] stats-service live — {STATS_BASE}")
        try:
            specs = fetch_inventory_specs(max_tables=28)
        except Exception as e:
            print(f"[fallback] stats-service 오류: {e}")
            print("[fallback] fixture 스펙으로 진행")
            specs = FIXTURE_SPECS
    else:
        print("[mode] fixture — TWIN_HUB_URL/TRIDENT_STATS_BASE_URL 미설정, fixture 스펙 사용")
        specs = FIXTURE_SPECS

    if not specs:
        print("[abort] 스펙이 비어있습니다.")
        sys.exit(1)

    print(f"\n[summary] 총 {len(specs)}개 테이블:")
    for s in specs:
        print(f"  {s['entity_id']:50s}  q={s['quality_score']:.2f}  {s['workload_fit']}")

    patch_create_scene(specs)
    print("\n[done] create_scene.py 패치 완료.")
    print("       Isaac Sim에서 아래 명령으로 USD 재생성 후 열어보세요:")
    print("       /isaac-sim/python.sh scripts/create_scene.py")


if __name__ == "__main__":
    main()
