# Trident-Twin

**Trident Data Lakehouse Pipeline Twin & AI Predictive Simulator (Phase 4)**

> A Study on Apache Iceberg-based Cloud-Native Trident Lakehouse for Scale-Across Infrastructure

## Overview

This repository contains the architecture overview and design documents for **Phase 4** of the Trident Lakehouse project — the **3D Digital Twin & AI Predictive Simulator** layer.

## Files

| File | Description |
|------|-------------|
| `overview.drawio` | Full architecture diagram (open with draw.io / diagrams.net) |
| `overview.png` | Architecture overview image |
| `draw_overview.py` | Python script used to generate overview.png |

## Architecture Summary

```
END                    EDGE                         CORE
─────────────────────────────────────────────────────────
Web Portal     →   Lakehouse Pipeline          →   FastAPI (Hub)
  Pipeline         Phase 1: Ingest                 PostgreSQL
  Control      →   Phase 2: Metadata Index     →   XGBoost (AI Model)
  Simulation   →   Phase 3: Search & Delivery  →   Omniverse Server
  3D Twin View ←──────────────── WebRTC ──────────────────
```

### Phase 4 Components

- **FastAPI** — Central hub: `/api/pipeline/*`, `/api/simulate/*`, `/api/twin/*`
- **PostgreSQL** — Nessie backend + Pipeline Execution Profiles accumulation
- **XGBoost** — AI prediction model trained on historical execution profiles
- **NVIDIA Omniverse** — 3D Pipeline Twin + Predictive Simulator + Dataset Health View

### Key Flows

1. **Pipeline Control** → FastAPI → Spark Operator (SparkApplication CRD)
2. **Pipeline Simulation** → FastAPI → XGBoost → predicted bottleneck/duration/resource
3. **Execution Profile** → PostgreSQL → XGBoost training data
4. **FastAPI /api/twin*** → Omniverse Kit Extension → USD Scene update
5. **Omniverse** → WebRTC → Web Portal 3D Twin View

## Related Repositories

- [Trident-Portal](https://github.com/mj006648/Trident-Portal) — Web Portal (Next.js + Tailwind CSS + FastAPI)
- [TwinX](https://github.com/mj006648/TwinX) — ArgoCD GitOps cluster management
