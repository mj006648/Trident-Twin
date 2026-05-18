# Trident Omniverse Twin Architecture

## Runtime path

```text
Trident Lakehouse Core
  ├─ Iceberg/Nessie: table/version/catalog state
  ├─ Redis: hot location/state metadata
  ├─ Milvus: explaining metadata vector search
  ├─ PostgreSQL: governance/catalog/accounting
  ↓
Stats Service Twin API
  ├─ /api/twin/entities
  ├─ /api/twin/state
  └─ /api/twin/events
  ↓
Omniverse Connector / Extension
  ↓
USD Stage
  ├─ /World/Lake
  ├─ /World/AccumulationPipeline
  ├─ /World/Metadata
  ├─ /World/Lakehouse
  ├─ /World/WorkloadInterfaces
  └─ /World/Datasets
  ↓
Isaac Sim WebRTC Viewer
  ↓
Trident Portal
```

## USD attribute convention

Every meaningful prim should carry stable Trident attributes.

```text
trident:entity_id
trident:entity_type
trident:stage
trident:zone
trident:metadata_status
trident:sharing_status
trident:last_event
```

## First scenario

```text
raw_arrived
→ stored_in_lake
→ explaining_metadata_generated
→ sharing_metadata_published
→ staged_in_lakehouse
→ requested_by_ai_workload
→ served_to_workload
```

## What Omniverse is not

Omniverse is not the catalog, storage layer, or metadata database. It is the spatial runtime projection of the current operational state.
