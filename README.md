# Trident-Twin

**NVIDIA Omniverse/Isaac Sim 기반 Trident Lakehouse Digital Twin PoC**

![Trident Twin Site Plan](docs/site-plan.png)

> Phase 5 Site Plan — 축적(Accumulation)·진열(Delivery) 파이프라인을 탑뷰로 표현.
> 좌표는 `scripts/create_scene.py`의 PoC USD stage와 1:1 일치 (1 unit = 1 m).
> 재생성: `python3 scripts/draw_site_plan.py`

> Trident Lakehouse의 `Lake → Metadata → Lakehouse → Staging/Serving → Workload Interface` 흐름을 USD stage, 상태 이벤트, Isaac Sim extension으로 표현하는 디지털 트윈 실험 저장소입니다.

## Overview

`Trident-Twin`은 Trident Lakehouse를 단순 대시보드로 보여주는 프로젝트가 아니라, 데이터셋·메타데이터·Lakehouse·워크로드 인터페이스를 **트윈 엔티티**, **상태 전이**, **이벤트 리플레이**, **운영 피드백 루프**로 연결하기 위한 PoC입니다.

현재 구현은 다음 질문에 답하기 위한 첫 번째 실행 가능한 skeleton입니다.

```text
데이터셋 하나가 Lake에 유입되고,
설명 메타데이터와 공유 메타데이터를 획득한 뒤,
Lakehouse에 진열되고,
AI/HPC/HPDA/M&S 워크로드에 의해 선택·제공되는 과정을
Omniverse 상에서 어떻게 상태 기반으로 표현할 것인가?
```

핵심 방향은 다음과 같습니다.

- **Omniverse/Isaac Sim**: 3D 공간, USD Prim, 상태 시각화, 이벤트 replay 담당
- **Trident Lakehouse**: Iceberg/Nessie 기반 데이터 저장·카탈로그 계층 담당
- **Metadata Layer**: Milvus 설명 메타데이터, Redis 공유/위치/상태 메타데이터, PostgreSQL 거버넌스 담당
- **Portal/Stats Service**: 운영자 UI, 상태 API, WebRTC viewer, 제어 루프 담당
- **AI Agent/RAG**: 향후 실행 이력 기반 병목 예측과 리소스 티어 추천 담당

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

## Twin Concept Mapping

사용자의 Lakehouse abstraction을 Omniverse runtime에서는 다음처럼 매핑합니다.

| Abstraction | Twin Entity | USD 표현 | 역할 |
| --- | --- | --- | --- |
| Lake | `lake.bronze` | `/World/Lake/BronzeLake` | raw/bronze 데이터 유입·저장 영역 |
| Accumulation Pipeline | `pipeline.accumulation` | `/World/AccumulationPipeline/*` | 데이터셋이 메타데이터를 획득하며 이동하는 축적 흐름 |
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
