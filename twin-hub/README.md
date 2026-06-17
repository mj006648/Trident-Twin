# twin-hub

FastAPI adapter that exposes Trident Lakehouse live state to the Omniverse Kit
extension using the same schema as the PoC fixtures
(`data/twin_entities.json`, `data/mock_twin_events.json`).

## Purpose (Phase 4, scope-bounded)

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

## Source bindings

`twin-hub` now supports a stats-service live adapter. The adapter intentionally
uses the Portal API instead of reaching into other people's Lakehouse containers.

| Source endpoint | Maps to twin state |
| --- | --- |
| `/api/v1/catalog/overview` | datasets, integrity, pipeline runs, Nessie commit |
| `/api/v1/catalog/datasets` | table name, namespace, row count, tags, owner, freshness |
| `/collection` | ready bundles / materialized collections from Redis |

The visual scene mirrors the current code path as seven operation cards:

1. `audit_run` → raw object
2. `catalog_dataset_upsert` → `catalog.datasets` row
3. `schema_snapshot_recorded` → `catalog.schema_versions` snapshot
4. `semantic_location_policy_attached` → Milvus/Redis/policy readiness bars
5. `search_index_refreshed` → searchable catalog index
6. `collection_or_join_created` → ready bundle / CTAS collection
7. `workload_delivery_snippet` → AI/HPC/HPDA usage package

## Modes

### Fixture mode

If `TRIDENT_STATS_BASE_URL` is unset, the hub serves the PoC fixtures directly so
the Kit extension keeps working offline.

```bash
cd twin-hub
uvicorn app:app --reload --port 8765
```

### Live stats-service mode

```bash
cd twin-hub
TRIDENT_STATS_BASE_URL=http://<trident-portal-stats-service>:<port> \
uvicorn app:app --host 0.0.0.0 --port 8765
```

Optional if the stats-service requires a bearer token:

```bash
export TRIDENT_STATS_TOKEN=<token>
```

The HTTP contract remains `/api/twin/entities`, `/api/twin/state`,
`/api/twin/events`, and `/api/twin/health`; only the source switches.
