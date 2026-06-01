# Trident-Twin

**Data Readiness / Usage Optimization Twin — Trident Lakehouse 공간 의사결정 인터페이스**

Trident-Twin은 Lakehouse를 3D로 꾸미는 뷰어가 아니라, Trident Portal 사용자가
"지금 쓸 수 있는 데이터가 무엇인지"를 한눈에 판단할 수 있는 **공간형 의사결정 지도**다.

## 씬 스크린샷

| 정상 90도 | 사선 45도 |
|:---------:|:---------:|
| ![top90](docs/screenshots/overview_top90.png) | ![top45](docs/screenshots/overview_top45.png) |

## 데이터 흐름 개요

![overview](overview.png)

## 씬 전경 (이전 버전)

![obli](docs/screenshots/Obli_Overview.png)

---

## 씬 레이아웃 (2026-05-31 기준)

| 번호 | 존 | 역할 | 중심 좌표 (x, y) |
|---|---|---|---|
| 1 | **TRUCK YARD** | 트럭 + 인바운드 컨베이어로 원시 데이터 반입 | (-22, 0) |
| 2 | **RAW BUCKET ZONE** | 창고 내부 5개 디렉터리 서브존, 태그 없는 갈색 박스 적재 | (-4, 11) |
| 3 | **ACCUMULATION ZONE** | 2개 컨베이어 벨트를 가로지르는 5개 보안검색대 게이트 | (+13, 0) |
| 4 | **LAKEHOUSE ZONE** | 통합 창고 — 하단 절반: 테이블 저장소, 상단 절반: 책꽂이 스테이징 | (+29, 11) |
| 5 | **SEARCH ZONE** | 로비 + 검색 카운터, 사용자 인텐트 → 후보 데이터 하이라이트 | (+44, +10) |
| 6 | **DELIVERY ZONE** | 통합 테이블 → 3개 아웃바운드 벨트 → AI/HPC/HPDA 트럭 | (+59, +10) |
| 7 | **CONTROL TOWER** | 운영자 뷰 — 레디니스, 병목, 라이브 상태 모니터링 | (-22, +25) |

### Accumulation Zone 게이트 5개

두 컨베이어 벨트(y=-0.7, y=+0.7)를 동시에 가로지르는 보안검색대 구조.
필러가 바닥에서 올라오고, 크로스바가 두 레인을 모두 덮으며, 색깔 배지가 작업 종류를 나타낸다.

| 스텝 | 작업 | 배지 색 | 생성 아티팩트 |
|---|---|---|---|
| 1 | `audit_run` | 브론즈 | raw object / ingest 결과 |
| 2 | `catalog_dataset_upsert` | 블루 | `catalog.datasets` 행 |
| 3 | `schema_snapshot_recorded` | 옐로 | `catalog.schema_versions` 스냅샷 |
| 4 | `semantic_location_policy_attached` | 퍼플 | Milvus/Redis/policy 바 |
| 5 | `search_index_refreshed` | 그린 | 검색 가능한 카탈로그 인덱스 |

### Lakehouse Zone 구조

- **하단 절반 (Y: -3.5 ~ +11.5)**: 테이블 저장소 — 4열 × 6행 실제 테이블, 위에 Iceberg 박스
- **상단 절반 (Y: +14.5 ~ +26.5)**: 스테이징 — 책꽂이 선반 유닛 12개, 3단 × 박스 3개

---

## l40s / Isaac Sim 배포 현황

| 항목 | 값 |
|---|---|
| 호스트 | `netai@l40s` |
| Isaac 컨테이너 | `isaac-sim-ICH-strongest` |
| Portal WebRTC 엔드포인트 | `10.38.38.197:49100` |
| 프로젝트 경로 (컨테이너 내) | `/mnt/Trident-Twin-520d314` |
| 최신 생성 씬 | `stages/trident_lakehouse_twin_<YYYYMMDD_HHMM>.usda` |
| 리플레이 씬 | `stages/trident_lakehouse_twin_replay.usda` |

### USD 씬 재생성

```bash
# 호스트에서 실행
cat scripts/create_scene.py | ssh netai@l40s \
  "sudo tee /mnt/Trident-Twin-520d314/scripts/create_scene.py > /dev/null"

ssh netai@l40s "sudo docker exec isaac-sim-ICH-strongest bash -c \
  'cd /mnt/Trident-Twin-520d314 && /isaac-sim/python.sh scripts/create_scene.py'"
```

Isaac Sim WebRTC에서 열기:
```
File > Open > /mnt/Trident-Twin-520d314/stages/trident_lakehouse_twin_<timestamp>.usda
```

---

## Lakehouse 라이브 연동 구조

```
Trident Portal stats-service (10.234.33.83)
  GET /api/v1/catalog/overview   → datasets, integrity, pipeline_runs
  GET /api/v1/catalog/datasets   → tags, namespace, row_count, size
  GET /collection                → ready bundles / materialized collections
        ↓  (HTTP, Bearer token)
twin-hub (uvicorn, port 8765)
  GET /api/twin/state            → entity_id → trident:* 속성 딕셔너리
        ↓  (HTTP polling, Kit update loop)
Isaac Sim extension (trident.twin)
  _on_update() → _fetch_state() → _apply_state()
  USD prim의 trident:* custom attribute를 매 N초마다 갱신
        ↓
Portal Digital Twin WebRTC 탭 (10.38.38.197:49100)
```

### 라이브 모드 실행

```bash
cd /mnt/Trident-Twin-520d314/twin-hub

# Keycloak 토큰 발급 (trident-baseline-runner service account)
TOKEN=$(kubectl exec -n trident deploy/stats-service -- \
  python3 -c "
import urllib.request, json, os
r = urllib.request.urlopen(urllib.request.Request(
  'http://10.38.38.220:8080/realms/trident/protocol/openid-connect/token',
  data='grant_type=client_credentials&client_id=trident-baseline-runner&client_secret=SECRET'.encode(),
  headers={'Content-Type':'application/x-www-form-urlencoded'}
))
print(json.loads(r.read())['access_token'])
")

TRIDENT_STATS_BASE_URL=http://10.234.33.83 \
TRIDENT_STATS_TOKEN=$TOKEN \
  uvicorn app:app --host 0.0.0.0 --port 8765
```

또는 `run_live.sh` 사용:
```bash
cd /mnt/Trident-Twin-520d314/twin-hub
TRIDENT_STATS_TOKEN=<token> bash run_live.sh
```

Isaac Sim에서 extension 활성화 후 **Start Live** 버튼 → `http://l40s-ip:8765` 입력.

---

## 연동 현황 및 남은 갭

### 현재 작동 중

| 항목 | 상태 |
|---|---|
| twin-hub fixture 모드 | 완료 — 토큰 없이 오프라인 테스트 가능 |
| twin-hub live 모드 | 완료 — stats-service `/catalog/overview`, `/catalog/datasets`, `/collection` 읽기 |
| Isaac Sim extension polling | 완료 — Kit update loop, 스레딩 없음 (크래시 없음) |
| USD `trident:entity_id` 매핑 | 완료 — `_build_index()`로 stage 순회 후 entity_id → prim path 인덱스 |
| 실제 live 데이터 반영 확인 | 완료 — `Live 7/25 prims updated` (7개 매칭) |

### 남은 갭 (우선순위 순)

#### 1순위: entity_id 정렬 (현재 7/25만 매칭)

**원인**: USD 씬의 entity_id가 fixture 네임스페이스(`camera`, `lidar`)를 사용하는데,
실제 Lakehouse 데이터는 `autonomous_test`, `autonomous_weather` 네임스페이스를 사용.

**해결 방법**:
- stats-service에서 실제 네임스페이스/테이블명을 읽어서 `create_scene.py`의
  `inventory_specs`를 동적으로 생성하는 스크립트 추가
- 또는 twin-hub가 entity_id를 USD 씬의 prim 이름 패턴에 맞게 매핑하는 변환 레이어 추가

```python
# twin-hub가 생성하는 entity_id 예시 (현재)
"table.autonomous_test.sensor_frames"

# USD 씬에 있어야 할 trident:entity_id (현재는 fixture)
"table.camera.frames"
```

**단기 해결책**: `create_scene.py`를 stats-service 데이터 기반으로 재생성하는
`scripts/sync_scene_from_live.py` 스크립트 작성.

#### 2순위: Keycloak 토큰 자동 갱신 (현재 1시간 TTL)

**원인**: `trident-baseline-runner` client_credentials 토큰은 1시간 후 만료.
twin-hub 재시작 없이는 401 에러 발생.

**해결 방법**: twin-hub 내부에 토큰 갱신 로직 추가.

```python
# twin-hub/app.py에 추가할 토큰 관리
class TokenCache:
    def __init__(self):
        self._token = os.getenv("TRIDENT_STATS_TOKEN", "")
        self._expires_at = 0.0
    
    def get(self) -> str:
        if time.time() < self._expires_at - 60:
            return self._token
        # client_credentials grant로 재발급
        ...
```

#### 3순위: Portal WebRTC ↔ USD prim 선택 동기화

**현재**: Portal Digital Twin 탭은 Isaac Sim WebRTC 스트림을 iframe으로 표시.
사용자가 Portal에서 데이터셋을 선택해도 USD 씬에서 해당 prim이 하이라이트되지 않음.

**해결 방법**:
- twin-hub에 `POST /api/twin/select` 엔드포인트 추가
- Isaac Sim extension에서 해당 entity_id의 prim을 선택/하이라이트
- Portal 검색 결과 클릭 → twin-hub → extension → USD prim 하이라이트

#### 4순위: WebSocket 스트림 (현재 HTTP polling)

**현재**: extension이 매 N초마다 `/api/twin/state` HTTP GET.
**개선**: `/api/twin/ws` WebSocket으로 diff만 푸시 → 반응 지연 제거.

---

## USD `trident:*` 속성 계약

twin-hub `/api/twin/state`가 반환하는 entity_id → 속성 딕셔너리가
Isaac Sim extension에 의해 USD prim의 custom attribute로 기록됨.

| USD 경로 패턴 | entity_id 패턴 | 주요 속성 |
|---|---|---|
| `/World/DataReadiness/RawObjects/RawObject_*` | `raw.object.01` ~ `raw.object.20` | `trident:object_count`, `trident:stage` |
| `/World/DataReadiness/ProcessFlow/Step_*` | `operation.01.audit_run` ~ `operation.05.*` | `trident:status`, `trident:step_no` |
| `/World/DataReadiness/Inventory/*/*` | `table.<namespace>.<component>` | `trident:row_count`, `trident:readiness_score`, `trident:quality_score` |
| `/World/DataReadiness/ReadyBundles/*` | `bundle.<name>` | `trident:confidence`, `trident:workload_fit` |
| `/World/DataReadiness/SearchSelection/*` | `search.intent.*` | `trident:candidate_count`, `trident:selection_state` |
| `/World/DataReadiness/WorkloadDelivery/*` | `delivery.package.<type>.*` | `trident:delivery_ready`, `trident:snippet_type` |

---

## 실제 stats-service 엔드포인트

| 엔드포인트 | 용도 | twin-hub 매핑 |
|---|---|---|
| `GET /api/v1/catalog/overview` | 전체 데이터셋 요약 + pipeline_runs | `_operation_entities()` |
| `GET /api/v1/catalog/datasets?limit=100` | 상세 테이블 정보 (row_count, tags, nessie_commit) | `_dataset_entity()` |
| `GET /collection` | Redis 기반 materialized collection 목록 | `_collection_entities()` |
| `POST /audit/run?namespace=<ns>` | 카탈로그 갱신 트리거 (Spark job) | twin-hub 미구현, 수동 호출 |

현재 Nessie 카탈로그에는 `autonomous_test`, `autonomous_weather` 2개 네임스페이스,
총 95개 엔트리 등록됨 (2026-05-28 기준).

---

## 시각 문법

| 시각 객체 | 의미 | 수량/밀도 |
|---|---|---|
| 갈색 박스 | 메타데이터 없는 원시 소스 오브젝트 | raw object count |
| 흰색 테이블 + Iceberg 박스 | 정제된 Iceberg 테이블 | 테이블 수, row/object 볼륨 |
| 보안검색대 게이트 | 파이프라인 작업 체크포인트 | 배지 색 = 작업 종류 |
| 책꽂이 선반 + 박스 | 스테이징된 레디 번들 / 컬렉션 | 선반 = 네임스페이스, 박스 = 테이블 |
| 금색/노란 번들 트레이 | 사용 준비된 큐레이션 번들 | 신뢰도 배지 |
| 보라색 패키지 | AI/HPC/HPDA 워크로드 딜리버리 패키지 | 딜리버리 큐 상태 |

---

## 저장소 구조

| 경로 | 설명 |
|---|---|
| `README.md` | 설계 및 연동 명세 |
| `scripts/create_scene.py` | Isaac Sim Python USD 씬 생성기 |
| `scripts/replay_events.py` | mock 이벤트 리플레이 적용 |
| `twin-hub/app.py` | FastAPI 상태 어댑터 (fixture + live 모드) |
| `twin-hub/run_live.sh` | stats-service 연결 live 실행 스크립트 |
| `exts/trident.twin/trident/twin/extension.py` | Omniverse Kit extension (polling loop) |
| `data/twin_entities.json` | fixture entity 정의 |
| `data/mock_twin_events.json` | fixture 이벤트 타임라인 |
| `stages/` | 생성된 USD 씬 파일들 |

---

## 제품 명제

핵심 질문은 "레이크하우스를 3D로 렌더링할 수 있는가?"가 아니다.

> **트윈이 테이블/리스트 UI만으로는 불가능한, 더 빠른 데이터 탐색 의사결정을 가능하게 하는가?**

유용한 Trident-Twin이 한눈에 답해야 하는 질문:

1. **어떤 데이터가 있는가?** — raw 파일, Iceberg 테이블, 파생 컬렉션
2. **얼마나 있는가?** — object count, 테이블 수, row 수, 네임스페이스/컴포넌트 밀도
3. **얼마나 정제되어 있는가?** — 스키마 레디니스, Iceberg 상태, quality score
4. **지금 바로 쓸 수 있는 것은?** — hot 데이터셋, Dataset Basket 항목, 레디 번들
5. **어디에 쓸 수 있는가?** — AI / HPC / HPDA 워크로드 딜리버리 패키지

---

## 연동 관련 다른 저장소

| 저장소 | 역할 |
|---|---|
| `Trident-Portal` | 검색, Dataset Basket, 워크로드 딜리버리, WebRTC 뷰어, stats-service |
| `TwinX-Ops` | Kubernetes / ArgoCD 배포 소스 오브 트루스 |
| `Trident-Twin` | 데이터 레디니스 트윈, USD 씬, 이벤트 리플레이, 라이브 상태 투영 |

---

## 설계 원칙

Omniverse는 소스 오브 트루스가 아니다.

```
소스 오브 트루스:
  Iceberg / Nessie / Redis / Milvus / PostgreSQL / Stats Service / Portal

트윈의 역할:
  레디니스, 메타데이터 커버리지, 사용 압력, 후보 번들,
  병목, 워크로드 딜리버리 상태의 공간적 투영
```

트윈은 사용자가 더 빠르고 나은 데이터 선택 결정을 내릴 수 있을 때만 가치 있다.
