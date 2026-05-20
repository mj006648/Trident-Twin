# Trident-Twin

**NVIDIA Omniverse/Isaac Sim 기반 Trident Lakehouse Digital Twin PoC**

![Trident Twin Conceptual Overview](overview.png)

> Conceptual Overview — Trident Lakehouse를 항만·창고·진열대·고객 응대로 비유한 개념도.
> Lake(트럭 유입) → Accumulation(컨베이어 위 메타 부여) → Lakehouse 진열대(Staging) → Adaptive Workload Interfaces(카트로 픽업하는 Delivery) → Operator(관제탑) 흐름을 보여준다.

![Trident Twin Site Plan](docs/site-plan.png)

> Phase 5 Site Plan — 위 개념도를 정확한 좌표 위에 매핑한 기술 평면도(탑뷰, X-Y).
> 4-Zone(Lake / Accumulation / Staging / Delivery) 모두 단일 Trident Lakehouse 외곽선 안에 위치.
> 좌표는 `scripts/create_scene.py`의 PoC USD stage와 1:1 일치 (1 unit = 1 m).
> 재생성: `python3 scripts/draw_site_plan.py`

![Trident Twin Elevation View](docs/elevation.png)

> Phase 5 Elevation View — Site Plan의 짝(사이드뷰, X-Z). Staging Shelf가 Silver Lakehouse 위로 z=1.7/2.1/2.5 m 에 적층되는 수직 구조를 보여준다. 탑뷰가 표현할 수 없는 entity 키 차이(Bronze Lake/Stations/Desks/Workload Docks)도 함께 확인 가능.
> 재생성: `python3 scripts/draw_elevation.py`

> Trident Lakehouse 내부의 **축적(Accumulation)** 과 **진열·전달(Staging/Delivery)** 파이프라인을 USD stage, 상태 이벤트, Isaac Sim extension으로 실시간 시각화하는 디지털 트윈 저장소입니다.

## Concept — Trident Lakehouse는 한 건물, 그 안에 네 개의 Zone

> 핵심 통찰: **Lake와 Lakehouse는 공간이 다른 두 시스템이 아니라, 같은 저장소(Ceph S3) 위에서 메타데이터가 부여되었는지에 따른 상태 차이**다.
> 따라서 Twin에서도 "Lake → Lakehouse 이동"이 아니라 **단일 Lakehouse 건물 안에서의 Zone 전이**로 표현한다.

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                            Trident Lakehouse                                 │
│                                                                              │
│   Lake Zone        Accumulation Zone     Staging Zone      Delivery Zone     │
│   ─────────        ─────────────────     ────────────      ──────────────    │
│   Raw/Bronze   →   Iceberg 구조화 +   →  자주 사용되는  →  Customer Desk     │
│   버킷 저장        설명/공유 메타       데이터셋 진열        (검색 → 진열대    │
│   (Ceph S3)        부여 (Milvus/         (Silver Iceberg     또는 메타 →     │
│                    Redis/Nessie)         + Redis hot)        워크로드 전달)   │
│                                                              │               │
│                                                              ▼               │
│                                                       AI · HPC · HPDA · M&S  │
└──────────────────────────────────────────────────────────────────────────────┘
```

| Zone | 한 줄 정의 | 데이터 상태 | 책임 컴포넌트 (Trident Phase) |
|------|-----------|----------|---------------------------|
| **Lake** | 사용자가 올린 raw/bronze 파일이 메타데이터 없이 그대로 저장되는 영역 | 데이터만 있음, 맥락 없음 (Data Swamp 위험 구간) | Ceph S3 버킷 (Phase 1 입력) |
| **Accumulation** | Lake 위의 파일들을 Iceberg 테이블로 구조화하고 설명·공유 메타데이터를 부여하는 작업장. 이 단계를 거쳐야 Lake가 Lakehouse로 승격됨 | Iceberg + Nessie commit + Milvus Super Context + Redis manifest cache | Phase 1 (Ingest) + Phase 2 (Catalog) |
| **Staging** | Accumulation을 마친 데이터셋 중 자주 검색·사용되는 인기 셋을 빠르게 꺼낼 수 있도록 진열대에 올려두는 구간 | Silver Iceberg 테이블 + Redis hot partition cache | Phase 1 Silver 출력 + Phase 3 Redis 가속 |
| **Delivery** | Customer Desk가 사용자 검색을 받아 ① Milvus 메타로 데이터를 찾거나 ② Staging 진열대에서 즉시 픽업하여 워크로드(AI/HPC/HPDA/M&S)에 전달하는 구간 | URI 리스트, Zero-Copy 핸드오프 | Phase 3 (Search) + Phase 4 (Delivery) |

### 두 파이프라인

- **Accumulation Pipeline (상행선)** — `Lake → Accumulation → Staging`. 사용자가 데이터를 올리면 메타가 붙고 진열대에 오른다.
- **Delivery Pipeline (하행선)** — `Customer query → Delivery → (Staging 또는 Milvus 메타) → Workload Dock`. 사용자가 데이터를 요청하면 진열대 또는 메타 검색을 통해 워크로드로 흘러나간다.

> M&S = **Modeling & Simulation** (전산 모사). USD prim 식별자에 `&`를 못 써서 prim 이름은 `MS`로 단축하지만 의미는 M&S와 동일하다.

## Overview

`Trident-Twin`은 위 4-Zone과 두 파이프라인을 **3D 공간 + 상태 전이 + 이벤트 replay**로 표현하기 위한 PoC이다. 단순 대시보드가 아니라:

- **공간**: 각 Zone과 그 안의 entity를 USD prim으로 배치 (Site Plan과 1:1)
- **상태**: 각 prim에 `trident:*` custom attribute로 현재 상태(stage/zone/metadata_status/sharing_status/last_event 등)를 기록
- **흐름**: Dataset Package가 Lake → Accumulation → Staging → Delivery 를 거치는 lifecycle을 mock event로 재생 (향후 Stats Service 실 source로 교체)
- **렌더**: Isaac Sim Kit extension이 상태 변화를 USD 속성에 반영, WebRTC로 Trident Portal에 스트리밍

핵심 분담:

- **Omniverse/Isaac Sim**: 3D 공간, USD prim, 상태 시각화, 이벤트 replay
- **Trident Lakehouse**: Iceberg/Nessie 기반 실 저장·카탈로그 계층 (state source of truth)
- **Metadata Layer**: Milvus(설명 메타) + Redis(공유/위치 메타) + PostgreSQL(거버넌스)
- **Portal/Stats Service**: 운영자 UI, 상태 API, WebRTC viewer
- **AI Agent/RAG**: Phase 5 비목표 — Intelligence Layer로 분리, 본 repo는 관측만

## Current Status

현재 저장소에는 **실제로 Isaac Sim Python으로 생성 가능한 USD stage**와 **mock event replay script**가 포함되어 있습니다.

완료된 항목:

- Trident Lakehouse Twin USD scene 생성
- Dataset Package, Lake, Lakehouse, Metadata Station, Workload Interface Prim 구성
- mock event 기반 dataset lifecycle replay
- USD custom attributes에 `trident:*` 상태 정보 기록
- Isaac Sim/Omniverse Kit extension skeleton 작성
- PoC 실행 방법 및 아키텍처 문서 작성

아직 남은 항목:

- Isaac Sim GUI에서 stage 시각 검수
- Extension enable 및 UI 동작 검증
- Stats Service/WebSocket/API 실시간 연동
- Portal `TridentTwin.tsx` viewer/state panel 연동
- 실제 Redis/Milvus/PostgreSQL/Iceberg/Nessie 상태 source 연결

## Repository Contents

| Path | Description |
| --- | --- |
| `README.md` | 저장소 개요, 실행 방법, 현재 구현 범위 |
| `overview.png` | Conceptual Overview 일러스트 (수작업, 항만·창고 비유) |
| `docs/site-plan.png` | Phase 5 Site Plan (좌표 1:1 기술 평면도, 탑뷰) |
| `docs/elevation.png` | Phase 5 Elevation View (사이드뷰, Staging Shelf 수직 적층 강조) |
| `docs/master-plan.md` | Phase 5 청사진: 좌표·entity 매핑·바인딩 표준·데모 시나리오·빌드 단계 |
| `data/twin_entities.json` | Twin entity 정의: Lake, Lakehouse, Metadata Station, Workload Interface, Dataset |
| `data/mock_twin_events.json` | Dataset lifecycle mock event sequence |
| `scripts/create_scene.py` | Isaac Sim Python 기반 기본 USD stage 생성 스크립트 |
| `scripts/replay_events.py` | mock event를 USD time samples/custom attributes로 반영하는 replay 스크립트 |
| `stages/trident_lakehouse_twin.usda` | 기본 Trident Lakehouse Twin USD stage |
| `stages/trident_lakehouse_twin_replay.usda` | 이벤트 replay가 반영된 USD stage |
| `exts/trident.twin/` | Omniverse Kit/Isaac Sim extension skeleton |
| `docs/omniverse-twin-poc.md` | PoC 실행 방법과 설계 메모 |
| `docs/twin-architecture.md` | Twin entity/state/event/backend 연동 아키텍처 |
| `archive/old/` | Phase 5 재정의 이전 회로도(`draw_overview.py` / `overview.drawio` / `overview.png`) 보관 |

## Twin Concept Mapping (4-Zone 기준)

사용자의 Lakehouse abstraction을 Omniverse runtime에서는 다음처럼 매핑한다.
(아래 표는 Site Plan과 PoC USD prim 양쪽 모두의 ground truth.)

### Lake Zone
| Twin Entity | USD prim | 역할 |
| --- | --- | --- |
| `lake.bronze` | `/World/Lake/BronzeLake` | Raw/Bronze 파일이 메타 없이 쌓이는 Ceph 버킷 영역 |

### Accumulation Zone
| Twin Entity | USD prim | 역할 |
| --- | --- | --- |
| `pipeline.accumulation` | `/World/AccumulationPipeline/InputConveyor` | Lake → 메타 부여 작업장으로의 이송 라인 |
| `station.metadata.explaining` | `/World/Metadata/ExplainingStation` | Milvus Super Context(설명 메타) 생성 지점 |
| `station.metadata.sharing` | `/World/Metadata/SharingStation` | Redis 기반 공유·위치 메타 발급 지점 |
| `pipeline.to_staging` | `/World/AccumulationPipeline/ToLakehouseConveyor` | 메타 부여 완료 후 Staging Zone으로의 이송 |

### Staging Zone
| Twin Entity | USD prim | 역할 |
| --- | --- | --- |
| `lakehouse.silver` | `/World/Lakehouse/SilverLakehouse` | Silver Iceberg 본체 (Staging 진열장 토대) |
| `shelf.silver.{1,2,3}` | `/World/Lakehouse/StagingShelf{1,2,3}` | 자주 사용되는 인기 데이터셋이 올려지는 진열 칸 |

### Delivery Zone
| Twin Entity | USD prim | 역할 |
| --- | --- | --- |
| `customer.desk` (예정) | `/World/Delivery/CustomerDesk` | 사용자 검색 접수창 — 본 단계에서 PoC USD에 신규 추가 예정 |
| `workload.ai.001` | `/World/WorkloadInterfaces/AI` | PyTorch SDK 픽업 도크 |
| `workload.hpc.001` | `/World/WorkloadInterfaces/HPC` | FUSE 마운트 픽업 도크 |
| `workload.hpda.001` | `/World/WorkloadInterfaces/HPDA` | Trino SQL 픽업 도크 |
| `workload.ms.001` | `/World/WorkloadInterfaces/MS` | M&S(Modeling & Simulation) 픽업 도크 |

### Cross-Zone (Lakehouse 전반)
| Twin Entity | USD prim | 역할 |
| --- | --- | --- |
| `operator.control` | `/World/Operations/OperatorDesk` | 운영자(시스템 관리) 관제 지점. Customer Desk와는 분리 |
| `dataset.sample.001` | `/World/Datasets/DatasetPackage001` | Lake → ... → Delivery 전 구간을 이동하는 lifecycle 주인공 |

> **레거시 호환 주의**: 현재 PoC USD의 일부 prim 경로(`/World/Lakehouse/...`)는 의미적으로는 Staging Zone에 속한다. PoC 호환을 위해 경로는 유지하되, Zone 라벨링은 본 표를 기준으로 한다.
| Explaining Metadata | `station.metadata.explaining` | `/World/Metadata/ExplainingStation` | 데이터셋 설명·의미·검색 컨텍스트 생성 지점 |
| Sharing Metadata | `station.metadata.sharing` | `/World/Metadata/SharingStation` | 위치·상태·공유 가능성·접근 정보를 부여하는 지점 |
| Lakehouse | `lakehouse.silver` | `/World/Lakehouse/SilverLakehouse` | 정리된 데이터셋이 진열되는 Silver/Serving 영역 |
| Staging/Serving | `pipeline.staging` | `/World/Lakehouse/StagingShelf*` | 워크로드 접근을 위한 데이터셋 진열·선택 영역 |
| Adaptive Workload Interface | `workload.*` | `/World/WorkloadInterfaces/*` | AI/HPC/HPDA/M&S 요청자 또는 실행 인터페이스 |
| Operator Desk | `operator.control` | `/World/Operations/OperatorDesk` | 운영자 관제·제어 지점 |
| Dataset Package | `dataset.sample.001` | `/World/Datasets/DatasetPackage001` | 상태 전이에 따라 이동하는 데이터셋 단위 |

## USD Scene Hierarchy

현재 PoC stage의 핵심 구조는 다음과 같습니다.

```text
/World
  /Lake
    /BronzeLake
  /AccumulationPipeline
    /InputConveyor
    /ToLakehouseConveyor
  /Metadata
    /ExplainingStation
    /SharingStation
  /Lakehouse
    /SilverLakehouse
    /StagingShelf1
    /StagingShelf2
    /StagingShelf3
  /WorkloadInterfaces
    /HPC
    /MS
    /AI
    /HPDA
  /Operations
    /OperatorDesk
  /Datasets
    /DatasetPackage001
      /ExplainingMetadataTag
      /SharingMetadataTag
```

## Dataset Event Replay

`data/mock_twin_events.json`에는 데이터셋 하나의 상태 전이 시나리오가 들어 있습니다.

```text
raw_arrived
→ stored_in_lake
→ explaining_metadata_generated
→ sharing_metadata_published
→ staged_in_lakehouse
→ requested_by_ai_workload
→ served_to_workload
```

각 이벤트는 USD stage에 다음 정보를 반영합니다.

- Dataset Package의 위치 이동
- `trident:stage` 상태 변경
- `trident:zone` 위치/구역 변경
- `trident:metadata_status` 변경
- `trident:sharing_status` 변경
- `trident:last_event` 기록
- time sample 기반 replay 가능성 확보

## Trident Custom Attributes

PoC는 단순 geometry만 만들지 않고, 향후 backend와 연결하기 위해 `trident:*` custom attributes를 사용합니다.

예시:

```text
trident:entity_id = dataset.sample.001
trident:entity_type = dataset
trident:stage = staged_in_lakehouse
trident:zone = lakehouse.silver
trident:metadata_status = explaining_ready
trident:sharing_status = published
trident:quality_score = 0.92
trident:access_frequency = 17
trident:last_event = served_to_workload
```

향후 실제 시스템에서는 `trident:entity_id`를 기준으로 아래 source와 연결합니다.

```text
Redis      → file location, serving state, cache state
Milvus     → explaining metadata, dataset semantic context
PostgreSQL → governance, catalog, lineage, access policy
Iceberg    → table/snapshot/manifest state
Nessie     → branch/tag/commit metadata
Stats API  → event stream, health score, execution profile
```

## Quick Start

### 1. Stage 생성

Isaac Sim Python을 사용해야 합니다. 일반 Python에서는 `pxr` 모듈이 바로 잡히지 않을 수 있습니다.

```bash
cd /home/chang/git/trident-omniverse-twin-poc

/home/chang/isaac-sim/python.sh scripts/create_scene.py
/home/chang/isaac-sim/python.sh scripts/replay_events.py
```

생성 결과:

```text
stages/trident_lakehouse_twin.usda
stages/trident_lakehouse_twin_replay.usda
```

### 2. Isaac Sim에서 확인

Isaac Sim GUI 실행 후 아래 파일을 엽니다.

```text
File → Open → stages/trident_lakehouse_twin_replay.usda
```

절대 경로:

```text
/home/chang/git/trident-omniverse-twin-poc/stages/trident_lakehouse_twin_replay.usda
```

### 3. 기본 검증

```bash
cd /home/chang/git/trident-omniverse-twin-poc

python3 -m json.tool data/twin_entities.json >/dev/null
python3 -m json.tool data/mock_twin_events.json >/dev/null
python3 -m py_compile scripts/create_scene.py scripts/replay_events.py exts/trident.twin/trident/twin/extension.py
test -s stages/trident_lakehouse_twin.usda
test -s stages/trident_lakehouse_twin_replay.usda
```

## Omniverse Extension Skeleton

Extension 경로:

```text
exts/trident.twin/
```

현재 목적:

- Isaac Sim/Kit extension 구조 확보
- mock event를 읽어 Dataset Package 상태를 갱신하는 기반 마련
- 향후 API/WebSocket 기반 live update로 확장

향후 목표:

```text
Stats Service /api/twin/entities
Stats Service /api/twin/events
WebSocket /ws/twin/state
Portal selection ↔ Omniverse Prim selection
Omniverse WebRTC viewer ↔ Trident Portal
```

## Target Architecture

```text
[Trident Portal]
  ├─ Twin Viewer / WebRTC
  ├─ Dataset Detail Panel
  ├─ Event Timeline
  └─ Operator Actions
          │
          ▼
[Stats Service / Twin API]
  ├─ /api/twin/entities
  ├─ /api/twin/state
  ├─ /api/twin/events
  ├─ /api/twin/replay
  └─ /ws/twin/state
          │
          ├──────────────► PostgreSQL
          │                 ├─ catalog / governance
          │                 ├─ lineage
          │                 └─ execution profiles
          │
          ├──────────────► Redis
          │                 ├─ location metadata
          │                 ├─ serving state
          │                 └─ cache freshness
          │
          ├──────────────► Milvus
          │                 └─ explaining metadata / vector context
          │
          ├──────────────► Iceberg / Nessie
          │                 ├─ table snapshots
          │                 ├─ manifests
          │                 └─ branches / tags
          │
          └──────────────► NVIDIA Omniverse / Isaac Sim
                            ├─ USD scene hierarchy
                            ├─ dataset state visualization
                            ├─ event replay
                            └─ operator interaction
```

## Roadmap

### Phase 1. Static Twin Scene

- USD stage hierarchy 구성
- Lake/Lakehouse/Metadata/Workload 공간 배치
- Dataset Package와 metadata tag 표현
- 기본 카메라/조명/재질 구성

### Phase 2. Event Replay Twin

- mock event sequence 정의
- Dataset lifecycle animation 반영
- `trident:*` custom attributes 기록
- 이벤트 timeline 기반 replay 확인

### Phase 3. Live State Twin

- Stats Service에 twin state API 추가
- WebSocket event stream 연결
- Redis/Milvus/PostgreSQL 상태를 Twin entity로 변환
- Isaac Sim extension에서 live update 수행

### Phase 4. Portal Integrated Twin

- `Trident-Portal`의 `TridentTwin.tsx`와 WebRTC viewer 연결
- Portal dataset selection과 Omniverse Prim selection 동기화
- Event timeline, health score, metadata panel 제공
- 운영자 action을 API로 전달

### Phase 5. Predictive Twin

- 실행 이력 기반 resource tier simulation
- Gold/Silver/Bronze 실행 시나리오 비교
- AI Agent/RAG 기반 병목 예측
- compaction, cache warm-up, re-indexing 같은 운영 제안 생성

## Integration with Other Repositories

| Repository | Role |
| --- | --- |
| `Trident-Portal` | Next.js 제어 포털, FastAPI stats-service, WebRTC Twin viewer, monitoring UI |
| `TwinX` | Kubernetes/ArgoCD GitOps 배포 매니페스트 |
| `Trident-Twin` | Omniverse/Isaac Sim Digital Twin, event replay, predictive simulation 구현 공간 |

## Design Principle

이 프로젝트에서 Omniverse는 source of truth가 아닙니다.

```text
Source of truth:
  Redis / Milvus / PostgreSQL / Iceberg / Nessie / Stats Service

Omniverse role:
  USD Prim hierarchy
  state visualization
  event replay
  simulation
  operator interaction
```

즉, 실제 데이터는 Lakehouse와 metadata backend에 있고, Omniverse는 그 상태를 **공간적으로 이해하고, 재생하고, 운영자가 상호작용할 수 있게 만드는 Twin layer**입니다.
