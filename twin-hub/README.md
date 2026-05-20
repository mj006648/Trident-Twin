# twin-hub

FastAPI adapter that exposes Trident Lakehouse live state to the Omniverse Kit
extension using the same schema as the PoC fixtures
(`data/twin_entities.json`, `data/mock_twin_events.json`).

## Purpose (Phase 5, scope-bounded)

- Serve a **read-only** view of current entity state and event stream.
- Replace mock JSON fixtures with real sources behind the same HTTP contract.
- **Not** a control plane: no execution, no prediction, no tier planning.

## Endpoints

| Method | Path | Returns |
| --- | --- | --- |
| GET | `/api/twin/entities` | Same shape as `data/twin_entities.json` |
| GET | `/api/twin/state` | Snapshot of `trident:*` attributes per entity |
| GET | `/api/twin/events?since=<ts>` | Append-only events matching `data/mock_twin_events.json` timeline schema |
| WS | `/api/twin/stream` | Push state diffs as they happen |
| GET | `/api/twin/health` | Liveness probe |

## Source bindings (planned)

| Source | Maps to |
| --- | --- |
| Nessie REST API | `trident:nessie_commit`, table count -> Lakehouse scale |
| PostgreSQL `catalog.*` | governance/lineage events, audit stream |
| Redis SCAN | partition cache freshness, URI list size |
| Milvus collection stats | vector count -> Explaining Station pulse |
| Trident-Portal stats-service | Spark job activity, workload sessions |

## Phase 5 stub mode

If the upstream sources are unavailable, the hub serves the PoC fixtures
directly so the Kit extension keeps working end-to-end during development.
The contract stays identical; only the source switches.

## Run (planned)

```bash
cd twin-hub
uvicorn app:app --reload --port 8765
```

Files will be added incrementally as bindings are wired up.
