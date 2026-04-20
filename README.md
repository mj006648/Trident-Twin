# Trident-Twin

**AI Agent-driven Data Pipeline Twin & Resource Predictive Simulator**

> Phase 5 of Trident Lakehouse: Gemma/RAG 기반 실행 예측, 리소스 티어링, NVIDIA Omniverse 3D 데이터 파이프라인 트윈.

## Overview

`Trident-Twin`은 Trident Lakehouse의 운영 효율을 높이기 위한 3D 관측·시뮬레이션 계층입니다. 기존 2D Portal이 데이터 인제스트, 검색, 분석, 계보 관리를 수행하는 제어 평면이라면, Trident-Twin은 파이프라인의 공간적 구조와 데이터 흐름을 3D로 표현하고 AI 에이전트가 실행 전 리소스 시나리오를 제안하는 예측 제어 평면입니다.

핵심 방향은 단순 통계 모델이 아니라 **PostgreSQL 실행 이력 + Milvus RAG + Gemma LLM Agent + Omniverse Twin**을 결합하는 것입니다.

## Repository Contents

| File | Description |
| --- | --- |
| `overview.drawio` | Trident Twin 전체 아키텍처 다이어그램 |
| `overview.png` | 다이어그램 이미지 |
| `draw_overview.py` | `overview.png` 생성용 보조 스크립트 |

## Architecture

```text
[Trident Portal]
  ├─ Pipeline Control
  ├─ Monitoring / Lineage
  └─ Twin Viewer
          │
          ▼
[FastAPI Twin Hub]
  ├─ /api/twin/state
  ├─ /api/twin/health
  ├─ /api/simulate/resource-tiers
  └─ /api/pipeline/execution-profile
          │
          ├──────────────► PostgreSQL
          │                 ├─ catalog datasets
          │                 ├─ lineage DAG
          │                 ├─ quality / integrity
          │                 └─ execution_profiles
          │
          ├──────────────► Milvus
          │                 └─ historical execution profile vectors
          │
          ├──────────────► Gemma LLM Agent
          │                 ├─ RAG 기반 병목 추론
          │                 ├─ Gold / Silver / Bronze 시나리오 생성
          │                 └─ Spark/Kubernetes 리소스 추천
          │
          └──────────────► NVIDIA Omniverse
                            ├─ Pipeline Twin
                            ├─ Predictive Simulator
                            └─ Dataset Health View
```

## Core Components

### 1. PostgreSQL Metadata & Execution Profiles

PostgreSQL은 Trident Catalog의 단일 거버넌스 저장소입니다.

- `catalog` schema: 데이터셋, 네임스페이스, RBAC, 검색 메타데이터
- `lineage` schema: S3 raw → Iceberg → search_index → Milvus/Redis 계보 DAG
- `quality` schema: Integrity Audit, 품질 규칙, SLO 위반 이력
- `execution_profiles`: Spark 실행 시간, CPU/GPU 사용률, 메모리 피크, I/O 처리량, 파티션 수, 카디널리티 엔트로피 등

Trident-Twin은 새 데이터셋 투입 전 이 실행 이력을 읽어 유사 워크로드를 찾고, 실제 실행 후에는 결과를 다시 축적하여 예측 품질을 개선합니다.

### 2. Milvus RAG over Historical Runs

과거 실행 프로파일은 정형 지표만 저장하지 않고, 데이터셋 특성과 실행 결과를 자연어/구조 혼합 컨텍스트로 변환해 Milvus에 임베딩합니다.

예시 컨텍스트:

```text
Dataset size: 2.1 TB
Format: image metadata + S3 URI pointers
Partition columns: date, weather, camera_id
File count: 18M
Spark workers: 12
Observed bottleneck: S3 metadata planning and shuffle skew
Duration: 47 min
```

새 인제스트 요청이 들어오면 데이터 크기, 스키마 복잡도, 파티션 구조, 파일 수, 예상 URI 밀도 등을 기준으로 유사 실행 사례 Top-K를 검색합니다.

### 3. Gemma LLM Agent

Gemma 기반 에이전트는 Milvus에서 검색한 과거 실행 사례와 PostgreSQL의 현재 카탈로그 상태를 함께 사용해 실행 계획을 추론합니다.

주요 역할:

- 병목 예측: S3 listing, Redis cache miss, Spark shuffle, GPU starvation, small-file 문제
- 리소스 티어 제안: Gold / Silver / Bronze
- Spark 설정 추천: executor 수, executor memory, cores, partition count
- 사전 최적화 제안: compaction, manifest refresh, Redis cache warm-up, Milvus re-indexing
- 사용자 승인용 설명 생성: 비용 대비 시간 단축 근거를 사람이 이해할 수 있게 요약

### 4. Resource Tier Simulation

새 데이터셋 투입 전 사용자는 세 가지 실행 시나리오를 비교합니다.

| Tier | Goal | Example Behavior |
| --- | --- | --- |
| Gold | 최고 성능 | A100/GPU 또는 최대 Spark executor 할당, 실행 시간 최소화 |
| Silver | 균형 | 비용과 시간을 균형화한 권장 기본값 |
| Bronze | 비용 최적화 | 유휴 자원 중심, 낮은 우선순위, 긴 실행 시간 허용 |

선택된 티어는 향후 Kubernetes/SparkApplication 설정으로 주입됩니다.

### 5. Omniverse 3D Pipeline Twin

3D Twin은 운영용 2D Portal을 대체하지 않고, 파이프라인 관측과 시뮬레이션 전용 뷰로 동작합니다.

공간 구성:

```text
Ingest Zone
  S3 raw objects → Spark structurize → Iceberg tables

Metadata Zone
  Iceberg manifest → Redis cache
  Dataset super context → Milvus vector
  Catalog/lineage → PostgreSQL

Workload Zone
  AI SDK / PyTorch
  HPC FUSE
  HPDA Trino SQL
```

데이터 이동은 파티클 흐름으로 표현하고, 병목 지점은 색상·속도·두께 변화로 표시합니다.

### 6. Dataset Health View

저장된 데이터셋의 상태를 3D 노드에 반영합니다.

건강도 산출 입력:

- Integrity Audit 비율
- Redis cache freshness
- Iceberg small-file / manifest 상태
- Milvus vector freshness
- 최근 검색/사용 빈도
- 품질 규칙 및 SLO 위반 여부

건강도가 낮은 노드는 Omniverse에서 색상과 크기가 변하며, Gemma Agent가 `re-indexing`, `compaction`, `snapshot expiration`, `cache refresh` 같은 최적화 시나리오를 제안합니다.

## Integration with Other Repositories

| Repository | Role |
| --- | --- |
| `Trident-Portal` | Next.js 제어 포털, FastAPI stats-service, 2D lineage/monitoring UI |
| `TwinX` | Kubernetes/ArgoCD GitOps 배포 매니페스트 |
| `Trident-Twin` | Omniverse Twin 및 AI predictive simulator 설계/구현 공간 |

## Current Scope

현재 이 레포는 Phase 5의 설계 문서와 다이어그램 중심입니다. 구현이 확장될 경우 다음 모듈을 추가하는 방향으로 진행합니다.

```text
twin-hub/
  FastAPI simulation API

agent/
  Gemma prompt templates
  RAG retrieval logic
  resource tier planner

omniverse-extension/
  USD scene generation
  live state update
  particle flow renderer

experiments/
  prediction accuracy tests
  resource-tier benchmark results
```

## Experiment Targets

추가 실험에서는 다음 지표를 우선 측정합니다.

1. 과거 실행 프로파일 기반 실행 시간 예측 오차
2. Gold/Silver/Bronze 티어별 처리 시간과 자원 사용량
3. Redis cache warm-up 유무에 따른 planning latency 차이
4. Iceberg compaction 전후 Spark job duration 변화
5. Dataset health score와 실제 파이프라인 실패/지연의 상관관계
6. Omniverse Twin이 표시한 병목 지점과 실제 execution profile의 일치율
