"""twin-hub: Trident Twin HTTP contract and Lakehouse live adapter.

Default mode is still the checked-in fixture so the Isaac extension can run
without a backend. Set TRIDENT_STATS_BASE_URL to the Portal stats-service base
URL to bind the same /api/twin/* contract to live Lakehouse metadata.

Live sources used from Trident-Portal/stats-service:
  - /api/v1/catalog/overview: datasets, integrity, pipeline_runs
  - /api/v1/catalog/datasets: tags, namespace, row_count, size
  - /collection: ready bundles/materialized collections in Redis

Run:
    TRIDENT_STATS_BASE_URL=http://<stats-service>:8000 uvicorn app:app --host 0.0.0.0 --port 8765
"""
from __future__ import annotations

import json
import os
import subprocess
import time

_live_proc: "subprocess.Popen | None" = None
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, Query
except ImportError:  # pragma: no cover - allows import without fastapi installed
    FastAPI = None  # type: ignore[assignment]
    Query = None  # type: ignore[assignment]

REPO_ROOT = Path(__file__).resolve().parents[1]
ENTITIES_FILE = REPO_ROOT / "data" / "twin_entities.json"
EVENTS_FILE = REPO_ROOT / "data" / "mock_twin_events.json"

TRIDENT_STATS_BASE_URL = os.getenv("TRIDENT_STATS_BASE_URL", "").rstrip("/")
HTTP_TIMEOUT_SECONDS = float(os.getenv("TRIDENT_TWIN_HTTP_TIMEOUT", "4"))

# Keycloak client_credentials 자동 갱신 설정
# TRIDENT_STATS_TOKEN을 직접 지정하면 자동 갱신 없이 해당 토큰 사용.
# TRIDENT_KC_* 환경변수를 설정하면 만료 60초 전에 자동으로 재발급.
_KC_URL = os.getenv("TRIDENT_KC_URL", "")           # e.g. http://10.38.38.220:8080/realms/trident/protocol/openid-connect/token
_KC_CLIENT_ID = os.getenv("TRIDENT_KC_CLIENT_ID", "trident-baseline-runner")
_KC_CLIENT_SECRET = os.getenv("TRIDENT_KC_CLIENT_SECRET", "")
_STATIC_TOKEN = os.getenv("TRIDENT_STATS_TOKEN", "")


class _TokenCache:
    """Keycloak client_credentials 토큰을 캐싱하고 만료 전에 자동 갱신한다."""

    def __init__(self) -> None:
        self._token: str = _STATIC_TOKEN
        self._expires_at: float = 0.0  # 정적 토큰이면 갱신 안 함

    def get(self) -> str:
        # 정적 토큰이 설정되어 있고 KC URL이 없으면 갱신 없이 반환
        if self._token and not _KC_URL:
            return self._token
        # 만료 60초 전에 갱신
        if time.monotonic() < self._expires_at - 60:
            return self._token
        return self._refresh()

    def _refresh(self) -> str:
        if not _KC_URL or not _KC_CLIENT_SECRET:
            return self._token  # KC 설정 없으면 기존 토큰 유지
        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": _KC_CLIENT_ID,
            "client_secret": _KC_CLIENT_SECRET,
        }).encode()
        req = urllib.request.Request(
            _KC_URL, data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        try:
            with urllib.request.urlopen(req, timeout=8.0) as r:
                payload = json.loads(r.read().decode())
            self._token = payload["access_token"]
            ttl = int(payload.get("expires_in", 3600))
            self._expires_at = time.monotonic() + ttl
            return self._token
        except Exception as e:
            raise LiveSourceError(f"Keycloak 토큰 갱신 실패: {e}") from e


_token_cache = _TokenCache()


class LiveSourceError(RuntimeError):
    pass


def load_entities() -> dict[str, Any]:
    with ENTITIES_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_events() -> dict[str, Any]:
    with EVENTS_FILE.open("r", encoding="utf-8") as f:
        return json.load(f)


STATE_KEYS = {
    "stage", "zone", "metadata_status", "sharing_status",
    "semantic_ready", "location_ready", "policy_ready",
    "quality_score", "readiness_score", "access_frequency",
    "freshness", "workload_fit", "selected_bundle", "delivery_package",
    "query", "candidate_count", "selection_state", "snippet_type",
    "source_bundle", "delivery_ready", "namespace", "component",
    "row_count", "object_count", "size_bytes", "confidence", "components",
    "source_operation", "operation", "step_no", "output_kind", "output_entity",
    "nessie_commit", "table_full_name", "integrity_pct", "s3_file_count",
    "index_row_count", "last_updated_at", "status", "job_type",
}


def _copy_trident_fields(bucket: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if key in {"id", "type", "name"}:
            continue
        if key in STATE_KEYS:
            bucket[f"trident:{key}"] = value


def _fetch_json(path: str) -> dict[str, Any]:
    if not TRIDENT_STATS_BASE_URL:
        raise LiveSourceError("TRIDENT_STATS_BASE_URL is not configured")
    req = urllib.request.Request(f"{TRIDENT_STATS_BASE_URL}{path}")
    token = _token_cache.get()
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        raise LiveSourceError(f"{path}: {e}") from e


def _split_table_name(table_full_name: str) -> tuple[str, str, str]:
    parts = [p.strip('"') for p in table_full_name.split(".") if p]
    if len(parts) >= 3:
        return parts[-3], parts[-2], parts[-1]
    if len(parts) == 2:
        return "trident", parts[0], parts[1]
    return "trident", "default", table_full_name or "unknown"


def _component_from_dataset(row: dict[str, Any]) -> str:
    _, namespace, table = _split_table_name(str(row.get("table_full_name", "")))
    name = table.lower()
    if any(k in name for k in ["camera", "frame", "image"]):
        return "camera"
    if any(k in name for k in ["lidar", "point", "track"]):
        return "lidar"
    if any(k in name for k in ["weather", "grid"]):
        return "weather"
    if any(k in name for k in ["gps", "trajectory", "location"]):
        return "gps"
    return namespace.lower() if namespace else "dataset"


def _freshness(last_updated_at: Any) -> str:
    if not last_updated_at:
        return "unknown"
    # Keep this intentionally coarse; stats-service owns exact time semantics.
    text = str(last_updated_at)
    return "fresh" if text[:10] == datetime.utcnow().date().isoformat() else "observed"


def _readiness_from_dataset(row: dict[str, Any]) -> float:
    integrity = row.get("integrity_pct")
    if integrity is not None:
        try:
            return max(0.0, min(1.0, float(integrity) / 100.0))
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


def _dataset_entity(row: dict[str, Any]) -> dict[str, Any]:
    table_full_name = str(row.get("table_full_name") or "unknown")
    _, namespace, table = _split_table_name(table_full_name)
    component = _component_from_dataset(row)
    readiness = _readiness_from_dataset(row)
    tags = row.get("tags") or []
    semantic_ready = bool(tags) or component in {"camera", "lidar", "weather", "gps"}
    location_ready = component in {"camera", "lidar", "gps", "weather"}
    policy_ready = row.get("sensitivity") not in {"restricted", "private"}
    return {
        "id": f"table.{namespace}.{table}".replace('"', "").lower(),
        "type": "iceberg_table",
        "name": table_full_name,
        "table_full_name": table_full_name,
        "namespace": namespace,
        "component": component,
        "zone": "zone.lakehouse_inventory",
        "stage": "lakehouse_inventory",
        "row_count": int(row.get("row_count") or 0),
        "object_count": int(row.get("s3_file_count") or row.get("index_row_count") or 0),
        "size_bytes": int(row.get("size_bytes") or 0),
        "quality_score": readiness,
        "readiness_score": readiness,
        "semantic_ready": semantic_ready,
        "location_ready": location_ready,
        "policy_ready": policy_ready,
        "freshness": _freshness(row.get("last_updated_at")),
        "access_frequency": 0,
        "workload_fit": "AI+HPDA" if component in {"camera", "lidar"} else "HPDA",
        "nessie_commit": row.get("nessie_commit"),
        "integrity_pct": row.get("integrity_pct"),
        "s3_file_count": row.get("s3_file_count"),
        "index_row_count": row.get("index_row_count"),
        "last_updated_at": str(row.get("last_updated_at") or ""),
    }


def _gate_status_from_audit(audit: dict[str, Any], gate_no: int) -> str:
    """audit 레코드 한 건에서 게이트 번호별 완료 상태를 추론한다.

    게이트→파이프라인 단계 대응:
      1 INGEST  - S3 raw 파일 도착  (s3_file_count > 0)
      2 STRUCT  - Iceberg 테이블 생성 (index_row_count > 0)
      3 INDEX   - search_index 저장  (integrity_pct 존재)
      4 EMBED   - Milvus+Redis 완료  (integrity_pct >= 90)
      5 AUDIT   - 최종 감사 통과     (status == "PASS")
    """
    s3_files   = int(audit.get("s3_file_count") or audit.get("s3_raw_files") or 0)
    index_rows = int(audit.get("index_row_count") or audit.get("index_rows") or 0)
    integrity  = audit.get("integrity_pct")
    passed     = audit.get("status") == "PASS"

    if gate_no == 1:
        return "done" if s3_files > 0 else "pending"
    if gate_no == 2:
        return "done" if index_rows > 0 else ("running" if s3_files > 0 else "pending")
    if gate_no == 3:
        return "done" if integrity is not None else ("running" if index_rows > 0 else "pending")
    if gate_no == 4:
        return "done" if (integrity or 0) >= 90 else ("running" if integrity is not None else "pending")
    if gate_no == 5:
        return "done" if passed else ("running" if (integrity or 0) >= 90 else "pending")
    return "pending"


def _operation_entities(pipeline_runs: list[dict[str, Any]], audit_by_ns: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Accumulation Zone 5개 게이트를 실제 trident-spark 파이프라인 단계와 매핑한다.

    trident_structurize.py → INGEST + STRUCT
    trident_index.py       → INDEX + EMBED + AUDIT
    """
    steps = [
        (1, "INGEST", "s3_raw_ingestion",      "raw_object",     "trident-raw"),
        (2, "STRUCT", "iceberg_structurize",    "iceberg_table",  "trident.{ns}.tables"),
        (3, "INDEX",  "search_index_build",     "search_index",   "trident.{ns}.trident_search_index"),
        (4, "EMBED",  "milvus_redis_indexing",  "vector_index",   "milvus.trident_semantic_catalog"),
        (5, "AUDIT",  "integrity_audit",        "audit_report",   "redis.trident:audit:{ns}"),
    ]

    # 네임스페이스 전체 audit를 집계해 게이트별 대표 상태 결정
    # 하나라도 running이면 running, 모두 done이면 done, 나머지 pending
    def _agg_gate(gate_no: int) -> str:
        if not audit_by_ns:
            return "pending"
        statuses = [_gate_status_from_audit(a, gate_no) for a in audit_by_ns.values()]
        if any(s == "running" for s in statuses):
            return "running"
        if all(s == "done" for s in statuses):
            return "done"
        if any(s == "done" for s in statuses):
            return "running"
        return "pending"

    latest = pipeline_runs[0] if pipeline_runs else {}
    entities = []
    for no, code_label, operation, output_kind, output_entity in steps:
        gate_status = _agg_gate(no)
        entities.append({
            "id": f"operation.{no:02d}.{operation}",
            "type": "pipeline_operation",
            "name": f"Step {no}: {code_label}",
            "code_label": code_label,
            "zone": "zone.refinement_pipeline",
            "stage": operation,
            "step_no": no,
            "operation": operation,
            "output_kind": output_kind,
            "output_entity": output_entity,
            "status": gate_status,
            "job_type": latest.get("job_type"),
            "nessie_commit": latest.get("nessie_commit"),
            # 게이트별 집계 수치
            "namespaces_done": sum(
                1 for a in audit_by_ns.values()
                if _gate_status_from_audit(a, no) == "done"
            ),
            "namespaces_total": len(audit_by_ns),
        })
    return entities


def _collection_entities(collections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    entities = []
    for item in collections[:12]:
        name = str(item.get("name") or item.get("table") or "collection")
        total_rows = int(item.get("total_rows") or 0)
        item_count = int(item.get("item_count") or len(item.get("items") or []))
        confidence = 0.80 + min(item_count, 4) * 0.03
        entities.append({
            "id": f"bundle.{name}".replace(" ", "_").lower(),
            "type": "ready_bundle",
            "name": name,
            "zone": "zone.staging_ready_bundles",
            "stage": "ready_bundle",
            "components": "+".join([str(x.get("table", "dataset")).split(".")[-2] for x in item.get("items", [])]) or "collection",
            "workload_fit": "AI+HPDA",
            "confidence": round(min(confidence, 0.96), 2),
            "readiness_score": round(min(confidence, 0.96), 2),
            "row_count": total_rows,
            "object_count": item_count,
            "policy_ready": True,
            "source_operation": "collection_or_join_created",
        })
    return entities


def _raw_bucket_entities(audit_by_ns: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """trident-raw S3 버킷 디렉터리 목록을 raw.{namespace} 엔티티로 변환."""
    try:
        s3_payload = _fetch_json("/stats/s3/list?bucket=trident-raw&prefix=&delimiter=/")
    except LiveSourceError:
        return []

    entities = []
    for entry in s3_payload.get("dirs", []):
        ns = entry["name"]
        audit = audit_by_ns.get(ns, {})
        index_rows = audit.get("index_row_count") or 0
        integrity = audit.get("integrity_pct")
        status = audit.get("status", "pending")
        # 서브디렉터리 수를 object_count 로 사용 (파일 구조 깊이 반영)
        try:
            sub = _fetch_json(f"/stats/s3/list?bucket=trident-raw&prefix={ns}/&delimiter=/")
            subdirs = len(sub.get("dirs", []))
            files = len(sub.get("files", []))
        except LiveSourceError:
            subdirs, files = 0, 0
        readiness = round(min((integrity or 0) / 100.0, 1.0), 2) if integrity is not None else 0.0
        entities.append({
            "id": f"raw.{ns}",
            "type": "raw_bucket",
            "name": ns,
            "namespace": ns,
            "zone": "zone.raw_bucket",
            "stage": "raw_ingestion",
            "index_row_count": index_rows,
            "integrity_pct": integrity,
            "s3_file_count": files,
            "object_count": subdirs + files,
            "status": status,
            "readiness_score": readiness,
            "quality_score": readiness,
            "last_updated_at": str(audit.get("timestamp", "")),
        })
    return entities


def load_live_entities() -> dict[str, Any]:
    overview = _fetch_json("/api/v1/catalog/overview")
    datasets_payload = _fetch_json("/api/v1/catalog/datasets?limit=100")
    try:
        collections_payload = _fetch_json("/collection")
    except LiveSourceError:
        collections_payload = {"collections": []}

    datasets_by_name: dict[str, dict[str, Any]] = {}
    for row in overview.get("datasets", []):
        datasets_by_name[str(row.get("table_full_name"))] = dict(row)
    for row in datasets_payload.get("datasets", []):
        key = str(row.get("table_full_name"))
        merged = datasets_by_name.setdefault(key, {})
        merged.update(dict(row))

    pipeline_runs = overview.get("pipeline_runs", []) or []
    entities = [_dataset_entity(row) for row in datasets_by_name.values() if row.get("table_full_name")]

    # audit 데이터를 먼저 수집 — operation entities와 raw bucket 모두에서 재사용
    try:
        audit_list = _fetch_json("/stats/audit")
    except LiveSourceError:
        audit_list = []
    audit_by_ns = {row["namespace"]: row for row in audit_list if row.get("namespace")}

    entities.extend(_operation_entities(pipeline_runs, audit_by_ns))
    entities.extend(_collection_entities(collections_payload.get("collections", []) or []))
    entities.extend(_raw_bucket_entities(audit_by_ns))
    return {
        "source": "live",
        "stats_base_url": TRIDENT_STATS_BASE_URL,
        "zones": load_entities()["zones"],
        "entities": entities,
        "pipeline_runs": pipeline_runs,
    }


def current_entities() -> dict[str, Any]:
    if TRIDENT_STATS_BASE_URL:
        try:
            return load_live_entities()
        except LiveSourceError as e:
            fallback = load_entities()
            fallback["source"] = "fixture_fallback"
            fallback["live_error"] = str(e)
            return fallback
    fixture = load_entities()
    fixture["source"] = "fixture"
    return fixture


def compute_state(entities_payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reduce the current entity source into latest trident:* attribute snapshot."""
    entities_payload = entities_payload or current_entities()
    state: dict[str, dict[str, Any]] = {}
    for entity in entities_payload["entities"]:
        bucket = {
            "trident:entity_id": entity["id"],
            "trident:entity_type": entity["type"],
            "trident:name": entity.get("name", entity["id"]),
        }
        _copy_trident_fields(bucket, entity)
        state[entity["id"]] = bucket

    # Fixture timelines still drive replay; live mode exposes pipeline runs as
    # state and deliberately avoids fabricating per-second events.
    if entities_payload.get("source", "fixture").startswith("fixture"):
        for ev in load_events()["timeline"]:
            target = ev["target"]
            bucket = state.setdefault(target, {"trident:entity_id": target})
            _copy_trident_fields(bucket, ev)
            bucket["trident:last_event"] = ev["event"]
            bucket["trident:source_timestamp"] = ev["time"]
    return {"source": entities_payload.get("source", "fixture"), "entities": state}


def filter_events(since: float | None) -> dict[str, Any]:
    timeline = load_events()["timeline"]
    if since is not None:
        timeline = [e for e in timeline if e["time"] > since]
    return {"timeline": timeline}


if FastAPI is not None:
    app = FastAPI(title="Trident Twin Hub", version="0.2.0")

    @app.get("/api/twin/health")
    def health() -> dict[str, Any]:
        if not TRIDENT_STATS_BASE_URL:
            return {"status": "ok", "mode": "fixture", "live_configured": False}
        try:
            overview = _fetch_json("/api/v1/catalog/overview")
            return {
                "status": "ok",
                "mode": "live",
                "live_configured": True,
                "dataset_count": len(overview.get("datasets", [])),
                "pipeline_run_count": len(overview.get("pipeline_runs", [])),
            }
        except LiveSourceError as e:
            return {"status": "degraded", "mode": "fixture_fallback", "live_configured": True, "error": str(e)}

    @app.get("/api/twin/entities")
    def entities() -> dict[str, Any]:
        return current_entities()

    @app.get("/api/twin/state")
    def state() -> dict[str, Any]:
        payload = current_entities()
        return compute_state(payload)

    @app.get("/api/twin/events")
    def events(since: float | None = Query(default=None)) -> dict[str, Any]:
        return filter_events(since)

    # ── Live Sync 제어 ────────────────────────────────────────────────────────
    ISAAC_CONTAINER = os.getenv("ISAAC_CONTAINER", "isaac-sim-ICH-strongest")
    SCENE_ROOT      = os.getenv("SCENE_ROOT",      "/mnt/Trident-Twin-520d314")
    ISAAC_PYTHON    = os.getenv("ISAAC_PYTHON",    "/isaac-sim/python.sh")

    @app.post("/api/twin/live/start")
    def live_start() -> dict[str, Any]:
        global _live_proc
        if _live_proc is not None and _live_proc.poll() is None:
            return {"status": "already_running", "pid": _live_proc.pid}

        twin_hub_url = os.getenv("TWIN_HUB_INTERNAL_URL", "http://localhost:8765")
        cmd = [
            "docker", "exec", ISAAC_CONTAINER,
            "bash", "-c",
            f"cd {SCENE_ROOT} && "
            f"TWIN_HUB_URL={twin_hub_url} "
            f"{ISAAC_PYTHON} scripts/live_sync.py"
        ]
        _live_proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        return {"status": "started", "pid": _live_proc.pid}

    @app.post("/api/twin/live/stop")
    def live_stop() -> dict[str, Any]:
        global _live_proc
        if _live_proc is None or _live_proc.poll() is not None:
            return {"status": "not_running"}
        _live_proc.terminate()
        try:
            _live_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _live_proc.kill()
        _live_proc = None
        return {"status": "stopped"}

    @app.get("/api/twin/live/status")
    def live_status() -> dict[str, Any]:
        if _live_proc is None:
            return {"running": False}
        running = _live_proc.poll() is None
        return {"running": running, "pid": _live_proc.pid if running else None}

else:  # pragma: no cover
    app = None  # type: ignore[assignment]
