"""Stdlib-only smoke test for twin-hub stub mode.

Verifies that the fixture-backed contract returns the shapes the Kit extension
expects, without requiring fastapi/uvicorn to be installed.

Run:
    python3 twin-hub/test_stub.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app  # noqa: E402


def assert_contains(d: dict, key: str) -> None:
    assert key in d, f"missing key: {key} in {list(d)[:5]}..."


def main() -> None:
    ents = app.load_entities()
    assert_contains(ents, "entities")
    assert any(e["id"] == "dataset.sample.001" for e in ents["entities"])

    evs = app.load_events()
    assert_contains(evs, "timeline")
    assert evs["timeline"][0]["event"] == "audit_run"

    st = app.compute_state()
    bucket = st["entities"]["dataset.sample.001"]
    assert bucket["trident:last_event"] == "served_to_workload"
    assert bucket["trident:stage"] == "served"
    assert bucket["trident:source_operation"] == "served_to_workload"

    filtered = app.filter_events(since=75)
    assert all(e["time"] > 75 for e in filtered["timeline"])
    assert filtered["timeline"], "expected at least one event after t=75"

    print("twin-hub stub OK:")
    print(f"  entities: {len(ents['entities'])}")
    print(f"  events:   {len(evs['timeline'])}")
    print(f"  state buckets: {len(st['entities'])}")
    print(f"  events since t=75: {len(filtered['timeline'])}")


if __name__ == "__main__":
    main()
