"""twin-hub: minimal FastAPI skeleton for the Trident Twin.

Phase 5, step S4: HTTP contract only. All endpoints currently serve the PoC
fixtures so the Kit extension (step S5) can move off file IO without waiting
for real source bindings. Real bindings (Nessie / PostgreSQL / Redis / Milvus
/ stats-service) replace the fixture loader behind the same contract in S6.

Run:
    uvicorn app:app --reload --port 8765

Quick check (no live server, no extra deps required for the stub itself):
    python -c "import app; print(app.load_entities()['entities'][0]['id'])"
"""
from __future__ import annotations

import json
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
    "row_count", "object_count", "confidence", "components",
}


def _copy_trident_fields(bucket: dict[str, Any], source: dict[str, Any]) -> None:
    for key, value in source.items():
        if key in {"id", "type"}:
            continue
        if key in STATE_KEYS:
            bucket[f"trident:{key}"] = value


def compute_state() -> dict[str, Any]:
    """Reduce the event timeline into the latest trident:* attribute snapshot
    per entity. In stub mode this folds the fixture timeline, but the schema is
    already aligned with the live Data Readiness vocabulary.
    """
    state: dict[str, dict[str, Any]] = {}
    for entity in load_entities()["entities"]:
        bucket = {
            "trident:entity_id": entity["id"],
            "trident:entity_type": entity["type"],
            "trident:name": entity.get("name", entity["id"]),
        }
        _copy_trident_fields(bucket, entity)
        state[entity["id"]] = bucket
    for ev in load_events()["timeline"]:
        target = ev["target"]
        bucket = state.setdefault(target, {"trident:entity_id": target})
        _copy_trident_fields(bucket, ev)
        bucket["trident:last_event"] = ev["event"]
        bucket["trident:source_timestamp"] = ev["time"]
    return {"entities": state}


def filter_events(since: float | None) -> dict[str, Any]:
    timeline = load_events()["timeline"]
    if since is not None:
        timeline = [e for e in timeline if e["time"] > since]
    return {"timeline": timeline}


if FastAPI is not None:
    app = FastAPI(title="Trident Twin Hub", version="0.1.0")

    @app.get("/api/twin/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "mode": "stub"}

    @app.get("/api/twin/entities")
    def entities() -> dict[str, Any]:
        return load_entities()

    @app.get("/api/twin/state")
    def state() -> dict[str, Any]:
        return compute_state()

    @app.get("/api/twin/events")
    def events(since: float | None = Query(default=None)) -> dict[str, Any]:
        return filter_events(since)
else:  # pragma: no cover
    app = None  # type: ignore[assignment]
