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


def compute_state() -> dict[str, Any]:
    """Reduce the event timeline into the latest trident:* attribute snapshot
    per entity. In Phase 5 stub mode this just folds the fixture timeline.
    """
    state: dict[str, dict[str, Any]] = {}
    for entity in load_entities()["entities"]:
        state[entity["id"]] = {
            "trident:entity_id": entity["id"],
            "trident:entity_type": entity["type"],
            "trident:stage": entity.get("stage"),
            "trident:zone": entity.get("zone"),
            "trident:metadata_status": entity.get("metadata_status"),
            "trident:sharing_status": entity.get("sharing_status"),
        }
    for ev in load_events()["timeline"]:
        target = ev["target"]
        bucket = state.setdefault(target, {"trident:entity_id": target})
        bucket["trident:stage"] = ev.get("stage", bucket.get("trident:stage"))
        bucket["trident:zone"] = ev.get("zone", bucket.get("trident:zone"))
        bucket["trident:metadata_status"] = ev.get(
            "metadata_status", bucket.get("trident:metadata_status")
        )
        bucket["trident:sharing_status"] = ev.get(
            "sharing_status", bucket.get("trident:sharing_status")
        )
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
