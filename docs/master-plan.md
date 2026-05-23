# Trident-Twin Master Plan (Phase 5 초기안 — v3 시점)

> ⚠️ **이 문서는 v3 시점의 master-plan으로 일부 내용이 현재(v11) 구현과 다르다.**
> 현재 구현 상태의 정확한 zone / coordinate / belt color 명세는
> [`/README.md`](../README.md) 와 [`/docs/v10-design.md`](v10-design.md)에 있다.
>
> 주요 변경:
> - 4-Zone 모델 (Lake / Accumulation / Staging / Delivery) → **3-stage 메탈 모델 (Bronze / Silver / Gold)**
> - 단일 Trident Lakehouse outline → **3 separate buildings (Raw / Lakehouse / Showcase)**
> - Audit Gate / Catalog Office → **제거됨**
> - Lobby + Search Counter → **단일 plaza로 통합**
> - 3개 dock 테이블 → **1개 Big Consolidation Table + 3 직선 outgoing belt**

> **Phase 5 정체성**
> Trident Lakehouse의 **축적(Accumulation)** 과 **진열(Delivery)** 파이프라인을
> 3D Omniverse Twin에서 **실시간으로 시각화**하는 단일 목적의 관측 평면.
> 예측·시뮬레이션은 본 Phase의 목표가 아니다.
>
> 본 문서는 `scripts/create_scene.py`로 생성되는 PoC USD stage 위에서
> 어떻게 Live 바인딩과 데모 시나리오를 확장할지를 정의한다.

---

## 1. 설계 원칙

1. **One Twin, Two Pipelines** — 축적 파이프(상행선)와 진열 파이프(하행선)만 보여준다.
2. **Live, not Static** — 모든 시각 요소는 Trident Lakehouse의 실 상태(Nessie 커밋, Spark Job, Redis 키, Milvus 컬렉션)에 바인딩된다. PoC의 mock event는 동일 인터페이스의 fixture에 불과하다.
3. **PoC USD as Source of Truth** — `stages/trident_lakehouse_twin.usda`의 prim 경로(`/World/Lake`, `/World/Lakehouse` 등)를 표준으로 채택. 본 문서는 그 위에 의미와 바인딩을 얹는다.
4. **Explainable in 3 Minutes** — 카메라 컷이 곧 논문 챕터. 심사위원이 3분 안에 "축적/진열이 무엇인지" 이해해야 한다.
5. **Expansion Slots** — 신규 엔진(Phase 6 GDS 등) 추가 시 `/World` 아래에 새 Scope만 추가, 기존 경로는 변경 금지.

---

## 2. 공간 레이아웃 (탑뷰)

PoC stage의 실제 X 좌표를 기준으로 한다 (`scripts/create_scene.py` 참고).

```
   X축 = 데이터 흐름 방향 (좌 → 우, 단위: meter)
   ─────────────────────────────────────────────────────────────▶

   X ≈ -9      -6.3       -2.5       +0.8      +3.5        +6~+8
   ┌─────────┬──────────┬──────────┬─────────┬──────────┬──────────┐
   │ Input   │ Bronze   │ Explain  │ Sharing │ Silver   │ Workload │
   │ Conveyor│ Lake     │ Station  │ Station │ Lakehouse│ Docks    │
   │         │          │          │         │ + Shelves│ AI/HPC/  │
   │         │          │          │         │          │ HPDA/MS  │
   └─────────┴──────────┴──────────┴─────────┴──────────┴──────────┘
       │           │           │          │          │          │
       ▼ 축적 파이프 (Cyan, 좌→우)                  ▼ 진열 파이프 (Green, 좌→우)
       raw_arrived → stored → explained → shared → staged → served

   상부: /World/Operations/OperatorDesk (관제)
   향후 확장: /World/Governance/* (Keycloak Tower, 수직 Z축)
```

---

## 3. Entity 카탈로그 (PoC 매핑)

`data/twin_entities.json`과 `stages/trident_lakehouse_twin.usda`를 기준으로 한다.

### 3.1 Accumulation 축
| Prim | Entity ID | 역할 | Live 바인딩 (목표) |
|------|----------|------|-------------------|
| `/World/Lake/BronzeLake` | `lake.bronze` | raw 데이터 유입 | Ceph 버킷 객체 수 → scale |
| `/World/AccumulationPipeline/InputConveyor` | `pipeline.accumulation.input` | 입력 컨베이어 | 활성 Spark Job 수 → 속도 |
| `/World/Metadata/ExplainingStation` | `station.metadata.explaining` | Milvus Super Context 생성 | Ollama 호출 시 발광 |
| `/World/Metadata/SharingStation` | `station.metadata.sharing` | Redis 위치/공유 메타 발급 | Redis SET 빈도 → 펄스 |
| `/World/AccumulationPipeline/ToLakehouseConveyor` | `pipeline.accumulation.output` | Lakehouse로 이송 | Nessie 커밋 빈도 → 속도 |

### 3.2 Delivery 축
| Prim | Entity ID | 역할 | Live 바인딩 (목표) |
|------|----------|------|-------------------|
| `/World/Lakehouse/SilverLakehouse` | `lakehouse.silver` | 진열대 본체 | Iceberg 테이블 수 → 크기 |
| `/World/Lakehouse/StagingShelf{1,2,3}` | `pipeline.staging.shelf*` | 워크로드별 진열 칸 | 활성 쿼리/세션 수 → 점등 |
| `/World/WorkloadInterfaces/AI` | `workload.ai.001` | PyTorch SDK 도크 | 활성 학습 Job 수 |
| `/World/WorkloadInterfaces/HPC` | `workload.hpc.001` | FUSE 마운트 도크 | 마운트 세션 수 |
| `/World/WorkloadInterfaces/HPDA` | `workload.hpda.001` | Trino SQL 도크 | 활성 쿼리 수 |
| `/World/WorkloadInterfaces/MS` | `workload.ms.001` | Modeling & Simulation | (Phase 6) |

### 3.3 Operator / Governance
| Prim | Entity ID | 역할 |
|------|----------|------|
| `/World/Operations/OperatorDesk` | `operator.control` | 관제 카메라 앵커, 알림 표시 |
| `/World/Datasets/DatasetPackage001` | `dataset.sample.001` | 7-stage replay의 주인공 |

---

## 4. 파이프라인 흐름 (파티클)

### 4.1 축적 파이프 (Cyan, 상행선)
PoC `mock_twin_events.json`의 timeline을 그대로 따른다.
```
raw_arrived (t=0)
  → stored_in_lake (t=25)
  → explaining_metadata_generated (t=50)
  → sharing_metadata_published (t=75)
  → staged_in_lakehouse (t=100)
```
- 색상: `#00d4ff`
- 정체(병목) 시 RED 전이 → 운영자 시각화

### 4.2 진열 파이프 (Green, 하행선)
```
requested_by_ai_workload (t=125)
  → served_to_workload (t=150)
```
- 색상: `#4ecb71`
- 향후: HPC/HPDA 워크로드 시나리오 추가, Milvus → Ollama → Redis 경로 시각화

---

## 5. `trident:*` 속성 표준

PoC에서 이미 사용 중 (`exts/trident.twin/trident/twin/extension.py`):
```
trident:entity_id
trident:entity_type
trident:stage
trident:zone
trident:metadata_status
trident:sharing_status
trident:last_event
trident:quality_score
trident:access_frequency
```

Phase 5 추가 권장:
```
trident:nessie_commit       # 마지막 반영된 Nessie commit hash
trident:source_timestamp    # 바인딩 source의 관측 시각
trident:health_color        # GRN/ORG/RED 단순화된 헬스
```

---

## 6. Twin Hub (FastAPI) 책임

PoC의 mock event를 실 source로 대체하는 어댑터 계층.
**예측·시뮬레이션 엔드포인트는 본 Phase에 포함하지 않는다.**

| Endpoint | 입력 | 출력 |
|----------|-----|------|
| `GET /api/twin/entities` | - | `data/twin_entities.json`과 동일 스키마, 실 source 기반 |
| `GET /api/twin/state` | - | 전체 엔티티 현재 `trident:*` 속성 스냅샷 |
| `GET /api/twin/events?since=` | timestamp | PoC `timeline`과 동일 스키마, append-only |
| `WS  /api/twin/stream` | - | 상태 변화 실시간 push |

소스: Trident-Portal stats-service, Nessie REST API, PostgreSQL catalog 스키마, Redis SCAN, Milvus collection stats.

---

## 7. 데모 시나리오 (3분, 논문 심사용)

| 시간 | 카메라 | 내레이션 |
|------|--------|---------|
| 0:00–0:30 | 전체 조감 | "Trident Lakehouse 전경. 좌측 Lake, 중앙 Metadata, 우측 Lakehouse + Workload Docks." |
| 0:30–1:30 | Accumulation 추적 | "Dataset Package가 Bronze Lake → Explaining → Sharing → Silver Lakehouse 로 흘러갑니다 (Cyan 파티클)." |
| 1:30–2:15 | Delivery 추적 | "AI 워크로드가 요청하면 Staging Shelf에서 Dataset이 워크로드 도크로 전달됩니다 (Green 파티클)." |
| 2:15–2:45 | Operator Desk 줌 | "운영자는 `trident:*` 속성과 이벤트 타임라인으로 모든 상태를 추적합니다." |
| 2:45–3:00 | 전체 조감 | "Trident = 축적과 진열의 단일 거버넌스 평면." |

카메라 프리셋은 `stages/trident_lakehouse_twin_replay.usda`에 추가 예정.

---

## 8. 단계별 빌드 순서

| 단계 | 산출물 | 상태 |
|-----|--------|------|
| **S1** | PoC USD stage + mock replay | **DONE** (`stages/`, `scripts/`, `exts/`) |
| **S2** | 본 master-plan.md (방향성·바인딩 표준) | **DONE** |
| **S3** | 카메라 프리셋 5종 (`stages/` 또는 별도 layer) | TODO |
| **S4** | `twin-hub/` FastAPI 골격 (`/api/twin/entities` 만) | TODO |
| **S5** | Kit Extension을 mock → twin-hub HTTP로 전환 | TODO |
| **S6** | 첫 실제 source 연동 (Nessie 커밋 수 → Iceberg 창고 scale) | TODO |
| **S7** | Accumulation/Delivery 파티클 시각화 | TODO |
| **S8** | District별 메시 디테일링 | TODO |
| **S9** | WebRTC 임베드 → Trident-Portal Monitoring 탭 | TODO |
| **S10** | 2D 마스터플랜 다이어그램 (논문 Figure) | TODO |

---

## 9. 확장성 (Phase 6 이후)

- 신규 엔진(예: NVIDIA GDS, 새로운 가속기) → `/World/` 아래 새 Scope 추가
- Governance 강화 → `/World/Governance/KeycloakTower` (수직 Z축)
- 신규 워크로드 → `/World/WorkloadInterfaces/` 아래 도크 추가
- 기존 prim 경로 변경 금지 (extension/script 호환성 유지)

---

## 10. Non-Goals (의도적으로 제외)

- 리소스 예측 모델 (XGBoost/Gemma 시뮬레이션은 본 Phase 아님)
- Gold/Silver/Bronze 티어 추천
- 비용 최적화 자동화
- Twin 안에서의 파이프라인 실행 제어 (Twin은 관측만 한다)

위 항목들은 Phase 6+에서 별도 평면(Intelligence Layer)으로 추가될 수 있다.
원래 PoC의 "AI Agent/RAG" 항목은 본 Phase에서 비활성화 상태로 두며,
`twin-hub/`의 어댑터 인터페이스만 갖춰 두어 후속 단계의 진입점이 되도록 한다.
