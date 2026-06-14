# Trident-Twin

**Trident Lakehouse Digital Twin — Trident Portal `/digital-twin`에서 보는 Lakehouse readiness / zone camera / data search bridge**

마지막 업데이트: **2026-06-14**

Trident-Twin은 Trident Lakehouse를 3D로 “예쁘게만” 보여주는 별도 제품이 아니다. Portal 사용자가 **어떤 raw dataset이 들어왔고, 어떤 Lakehouse table로 materialize 됐고, 어떤 데이터를 검색/선택해서 다음 분석으로 넘길 수 있는지**를 빠르게 판단하도록 돕는 **read-mostly Digital Twin viewer + event bridge**이다.

현재 구현 기준에서 안전하게 주장할 수 있는 범위는 다음과 같다.

- Portal **Digital Twin** 메뉴에서 Isaac Sim / Omniverse WebRTC stream을 임베드한다.
- 우측 패널은 **Zone Camera**와 **Data Search** 중심으로 동작한다.
- Data Search에서 결과를 선택하면 같은 탭 아래에서 **Gemma4 Q&A**로 선택 데이터에 대해 질문할 수 있다.
- `twin-hub`는 Portal과 Isaac extension 사이의 HTTP bridge다.
- scene 생성 시 Raw Bucket Zone과 Lakehouse Zone은 `twin-hub /api/twin/entities`의 live entity를 읽어 서로 맞춰 생성한다.
- 무거운 catalog/search/S3 조회는 계속 polling하지 않고, TTL cache 또는 사용자 click/submit 시점에만 수행한다.

명확한 non-goal:

- Omniverse가 catalog/storage/governance source of truth가 아니다.
- 폐루프 자동 제어(closed-loop control)를 완성한 시스템이라고 말하지 않는다.
- 모든 Portal event가 frame 단위 실시간 양방향 동기화된다고 과장하지 않는다.
- 검색, catalog, S3 전체 스캔을 짧은 주기로 계속 돌리지 않는다.

---

## 1. 2026-06-14 현재 운영 상태

| 항목 | 현재 값 |
| --- | --- |
| Portal image | `ich6648/trident-portal:v97.136` |
| twin-hub image | `ich6648/trident-twin-hub:v0.1.2` |
| GitOps 반영 | `SmartX-Team/TwinX-Ops` PR [#167](https://github.com/SmartX-Team/TwinX-Ops/pull/167) merged |
| Portal service | `http://10.38.38.217` |
| Portal → twin-hub | `http://trident-twin-hub.trident.svc.cluster.local:8765` |
| Portal → Isaac signaling | `10.38.38.197:49100` |
| twin-hub LoadBalancer | `http://10.38.38.223:8765` |
| Isaac container | `ssh netai@l40s`, Docker container `isaac-sim-ICH-strongest` |
| 최신 확인 scene | `/mnt/Trident-Twin-520d314/stages/trident_lakehouse_twin_20260614_2234.usda` |

최근 검증:

- `npm run build` in `Trident-Portal`
- `python3 -m py_compile scripts/create_scene.py twin-hub/app.py scripts/sync_scene_from_live.py`
- `docker push ich6648/trident-portal:v97.136`
- `docker push ich6648/trident-twin-hub:v0.1.2`
- l40s ICH stream: `Isaac Sim Full Streaming App is loaded`
- generated USD 안에서 `lakehouse.slot.icu_waveform_mixed_v1`, `raw.icu_waveform_mixed_v1`, `trident:table_role = "data"/"metadata"` 확인

---

## 2. 관련 저장소와 책임

| 저장소 | 실제 역할 | Trident-Twin과의 연결 |
| --- | --- | --- |
| [`SmartX-Team/TwinX-Ops`](https://github.com/SmartX-Team/TwinX-Ops) | 실제 클러스터 배포 ArgoCD/GitOps repo | `trident-portal`, `trident-twin-hub` image/env/source of truth |
| [`mj006648/Trident-Portal`](https://github.com/mj006648/Trident-Portal) | 실제 사용자 포탈 | `/digital-twin`, Isaac viewer, Zone Camera, Data Search, Gemma4 Q&A |
| [`mj006648/Trident-Lakehouse`](https://github.com/mj006648/Trident-Lakehouse) | 연구/논문/phase 정리 repo | Twin의 연구 주장 범위와 Lakehouse phase 정의 기준 |
| [`mj006648/Trident-Twin`](https://github.com/mj006648/Trident-Twin) | Digital Twin 구현 repo | USD scene generator, `twin-hub`, Isaac extension, live sync helper |

---

## 3. 전체 흐름

```text
Portal /digital-twin
  ├─ /api/digital-twin/config
  │    └─ returns ISAAC_SIM_HOST=10.38.38.197, ISAAC_SIM_SIGNALING_PORT=49100
  ├─ IsaacSimViewer
  │    └─ NVIDIA Omniverse WebRTC direct stream
  └─ right panel
       ├─ Zone Camera
       │    └─ /api/digital-twin/camera → twin-hub /api/twin/camera
       └─ Data Search
            ├─ Portal search API
            ├─ selected result → /api/digital-twin/highlight → twin-hub /api/twin/highlight
            └─ selected result + question → /api/digital-twin/gemma/ask → Gemma4 vLLM

Isaac Sim / trident.twin extension
  ├─ light polling: twin-hub /api/twin/commands?since=<seq>
  ├─ optional live polling: twin-hub /api/twin/entities
  └─ applies camera/highlight/live boxes onto USD stage

Scene generation
  ├─ scripts/create_scene.py
  ├─ fetches twin-hub /api/twin/entities at generation time
  ├─ creates Raw Bucket dataset slots
  └─ mirrors actual Lakehouse tables into matching Lakehouse slots
```

Source of truth 원칙:

```text
Lakehouse source of truth:
  Iceberg / Nessie / Redis / Milvus / PostgreSQL / stats-service / Portal

Twin 책임:
  viewer, zone camera, readiness visualization, search selection highlight,
  selected data context handoff to Gemma4
```

---

## 4. 계속 연동할 것 vs 한 번만 연동할 것

랙을 줄이기 위해 연동을 세 종류로 분리한다.

| 구분 | 계속 유지 | click/submit 시점 | 일회성/명시적 작업 |
| --- | --- | --- | --- |
| WebRTC stream | Portal Digital Twin 탭이 열려 있을 때 Isaac stream 유지 | 해당 없음 | stale stream이면 ICH stream 프로세스만 재시작 |
| Camera | Isaac extension이 command queue를 가볍게 polling | Zone Camera 클릭 시 camera command 1건 생성 | camera preset 추가/삭제는 code + image + GitOps PR |
| Search highlight | 계속 polling하지 않음 | 검색 결과 선택 시 highlight command 1건 생성 | USD entity id contract 변경 시 scene 재생성 |
| Data Search | 자동 polling 없음 | 사용자가 Search 버튼을 누를 때 Portal search API 호출 | 검색 API schema 변경 시 Portal adapter 수정 |
| Gemma4 Q&A | 자동 호출 없음 | 선택 데이터 + 질문 제출 시 vLLM 호출 | 모델/endpoint 변경은 TwinX-Ops env 수정 |
| Raw/Lakehouse scene | scene 생성 시 live entity를 1회 조회 | 해당 없음 | raw bucket/table 구조가 크게 바뀌면 USD 재생성 |
| Isaac live boxes | extension `Start Live` 이후에만 `/api/twin/entities` polling | ingest/camera/highlight command 반영 | 기본 static scene 자체는 PR/scene generation으로 관리 |
| stats-service catalog/S3 | `twin-hub` TTL cache로 보호 | 필요 시 API request | frame 단위/짧은 주기 전체 스캔 금지 |

---

## 5. Zone / camera 정의

Portal에 노출하는 camera는 현재 다음만 사용한다. **Ingest Zone camera는 Portal에서 제거했다.**

| Camera id | Label | USD camera path | 의미 |
| --- | --- | --- | --- |
| `overview` | `Overview Full` | `/World/Cameras/Overview_Top45` | 전체 45도 조망 |
| `raw_bucket` | `Raw Bucket Zone` | `/World/Cameras/zone_02_raw_bucket` | raw dataset namespace slot |
| `accumulation` | `Accumulation Zone` | `/World/Cameras/zone_03_accumulation` | PROFILE→READY operation pipeline |
| `lakehouse` | `Lakehouse Zone` | `/World/Cameras/zone_04_lakehouse` | raw dataset에 대응되는 actual table slot |
| `search` | `Search Zone` | `/World/Cameras/zone_05_search` | search/readiness decision area |
| `delivery` | `Delivery Zone` | `/World/Cameras/zone_06_delivery` | AI/HPC/HPDA handoff 표현 |
| `tower` | `Control Tower Zone` | `/World/Cameras/zone_07_tower` | 운영자/전체 관제 anchor |

Scene 내부에는 Truck Yard/Ingest 표현이 남아 있을 수 있지만, Portal camera UX에서는 핵심 흐름에서 제외한다.

---

## 6. Raw Bucket Zone ↔ Lakehouse Zone live-linked 생성

오늘 기준 가장 중요한 정의는 이 부분이다.

### 의도

Raw Bucket Zone에 `icu_waveform_mixed_v1` dataset slot이 있다면, Lakehouse Zone에도 같은 dataset slot이 있고 그 안에 실제로 생성된 table들만 표시한다.

예:

```text
Raw Bucket Zone
  icu_waveform_mixed_v1

Lakehouse Zone
  lakehouse.slot.icu_waveform_mixed_v1
    ├─ table.icu_waveform_mixed_v1.<data-table-1>       role=data
    ├─ table.icu_waveform_mixed_v1.<data-table-2>       role=data
    ├─ table.icu_waveform_mixed_v1.<data-table-3>       role=data
    └─ table.icu_waveform_mixed_v1.<metadata-table-1>   role=metadata
```

### 구현

`scripts/create_scene.py`는 scene 생성 시 다음 순서로 동작한다.

1. `TWIN_HUB_URL` 또는 `TRIDENT_TWIN_HUB_URL`을 읽는다.
   - 기본값: `http://10.38.38.223:8765`
2. `GET /api/twin/entities`에서 `raw_bucket` entity를 읽어 Raw Bucket namespace list를 만든다.
3. Raw Bucket Zone에 namespace별 slot을 생성하고, 각 namespace의 slot center를 기록한다.
4. 같은 `/api/twin/entities`에서 `iceberg_table` entity를 읽는다.
5. table entity를 namespace별로 group한다.
6. Raw slot coordinate를 Lakehouse lower area로 map해서 `lakehouse.slot.<namespace>`를 만든다.
7. 그 slot 안에 실제 table crate를 배치한다.
8. table component 이름으로 role을 추론한다.
   - `manifest`, `metadata`, `catalog`, `asset`, `schema`, `lineage`, `link`, `index` 포함 → `metadata`
   - 그 외 → `data`
9. `data`와 `metadata` table crate는 서로 다른 material/color를 사용한다.

하드코딩된 inventory list는 live 조회 실패 시 fallback으로만 남아 있다. 정상 경로에서는 `twin-hub` live entity가 우선이다.

`scripts/sync_scene_from_live.py`는 더 이상 `create_scene.py` inventory block을 덮어쓰지 않는다. 지금은 live inventory를 확인하는 compatibility no-op이며, stale snapshot이 live-linked scene generator를 망가뜨리지 않게 막는다.

---

## 7. Pipeline / entity schema

현재 pipeline operation은 과거 5-step 고정이 아니라 catalog-first 7-step 모델이다.

| Step | Code | Operation | Output kind |
| --- | --- | --- | --- |
| 1 | `PROFILE` | `object_schema_profile` | `asset_registry` |
| 2 | `MATERIAL` | `cardinality_materialize` | `iceberg_table` |
| 3 | `CATALOG` | `catalog_tables_columns` | `catalog_metadata` |
| 4 | `LINK` | `asset_link_audit` | `link_audit` |
| 5 | `GRAPH` | `redis_component_graph` | `component_graph` |
| 6 | `SEMANTIC` | `milvus_semantic_index` | `semantic_index` |
| 7 | `READY` | `dataset_ready_status` | `dataset_manifest` |

`twin-hub`가 주로 반환하는 entity type:

| Entity type | 의미 | 사용처 |
| --- | --- | --- |
| `raw_bucket` | raw dataset namespace/status | Raw Bucket Zone, live boxes, scene dataset slot |
| `pipeline_operation` | PROFILE→READY operation status | Accumulation Zone |
| `iceberg_table` | 실제 Lakehouse table/data product | Lakehouse Zone actual table crates |
| `ready_bundle` | basket/collection/CTAS 후보 | Showcase/Delivery 후보 |
| `search_highlight` | Portal search selection | Search Zone highlight |
| `workload_delivery_package` | AI/HPC/HPDA handoff package | Delivery Zone |
| `operator` | viewer/operator anchor | Control Tower Zone |

USD prim에는 가능한 한 다음 `trident:*` custom attribute를 붙인다.

```text
trident:entity_id
trident:entity_type
trident:name
trident:zone
trident:stage
trident:namespace
trident:component
trident:table_role
trident:readiness_score
trident:quality_score
trident:semantic_ready
trident:location_ready
trident:policy_ready
trident:last_event
```

---

## 8. `twin-hub` HTTP contract

`twin-hub`는 FastAPI adapter다. Portal과 Isaac extension이 동일한 `/api/twin/*` schema를 보게 한다.

| Method | Path | 동작 |
| --- | --- | --- |
| `GET` | `/api/twin/health` | fixture/live/degraded 상태 반환 |
| `GET` | `/api/twin/cameras` | Zone Camera preset 반환 |
| `POST` | `/api/twin/camera` | camera switch command append |
| `POST` | `/api/twin/highlight` | entity highlight command append |
| `GET` | `/api/twin/commands?since=<seq>` | 아직 처리하지 않은 camera/highlight command 반환 |
| `POST` | `/api/twin/ingest/event` | Portal ingest event snapshot 저장 |
| `GET` | `/api/twin/ingest/active` | active ingest namespace/event 반환 |
| `DELETE` | `/api/twin/ingest/clear` | active ingest event snapshot 초기화 |
| `GET` | `/api/twin/entities` | fixture 또는 live entity 목록 반환. base entity는 TTL cache 적용 |
| `GET` | `/api/twin/state` | entity를 `trident:*` style state snapshot으로 reduce |
| `GET` | `/api/twin/events?since=<ts>` | fixture timeline event 반환 |
| `POST` | `/api/twin/live/start` | optional live sync process 시작 시도 |
| `POST` | `/api/twin/live/stop` | optional live sync process 중지 |
| `GET` | `/api/twin/live/status` | optional live sync process 상태 반환 |

환경변수:

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `TRIDENT_STATS_BASE_URL` | unset | live stats-service base URL. unset이면 fixture mode |
| `TRIDENT_TWIN_HTTP_TIMEOUT` | `4` | stats-service/twin-hub HTTP timeout seconds |
| `TRIDENT_TWIN_ENTITY_CACHE_TTL` | `30` | base entity cache TTL seconds |
| `TRIDENT_TWIN_MAX_COMMANDS` | `80` | command queue max length |
| `TRIDENT_STATS_TOKEN` | unset | static Bearer token |
| `TRIDENT_KC_URL` | unset | Keycloak client_credentials token endpoint |
| `TRIDENT_KC_CLIENT_ID` | `trident-baseline-runner` | Keycloak client id |
| `TRIDENT_KC_CLIENT_SECRET` | unset | Keycloak client secret. Git에 넣지 말고 OpenBao/ESO/K8s Secret으로 주입 |

---

## 9. Portal Digital Twin contract

Portal 쪽 주요 파일:

| Portal 파일 | 역할 |
| --- | --- |
| `src/app/(app)/digital-twin/page.tsx` | viewer + right panel. `Zone Camera`, `Data Search`, embedded Gemma4 Q&A |
| `src/components/IsaacSimViewer.tsx` | Isaac stream wrapper와 read-only overlay |
| `src/components/digital-twin/AppStream.tsx` | NVIDIA Omniverse WebRTC direct client |
| `src/app/api/digital-twin/config/route.ts` | Isaac host/port 반환 |
| `src/app/api/digital-twin/health/route.ts` | twin-hub health proxy |
| `src/app/api/digital-twin/cameras/route.ts` | twin-hub cameras proxy + fallback |
| `src/app/api/digital-twin/camera/route.ts` | camera command proxy |
| `src/app/api/digital-twin/highlight/route.ts` | highlight command proxy |
| `src/app/api/digital-twin/gemma/ask/route.ts` | selected data + question → Gemma4 vLLM |
| `src/app/api/digital-twin/event/route.ts` | ingest event best-effort forwarding |

현재 UX 원칙:

- `Digital Twin Control` header는 가운데 정렬한다.
- live/status badge를 UI에 노출하지 않는다.
- Camera 탭 이름은 `Zone Camera`다.
- Data Search와 Gemma4 Q&A는 분리된 탭이 아니다. Search 결과 선택 후 같은 탭 아래에서 Q&A한다.
- Ingest Zone camera는 Portal에 노출하지 않는다.
- 검색 자체는 Digital Twin에서 주기 polling하지 않고 사용자가 Search를 눌렀을 때만 호출한다.

Gemma4 연동:

| 변수 | 예시 |
| --- | --- |
| `GEMMA4_BASE_URL` | `http://gemma4-vllm-backend.sjpark.svc.cluster.local:8000` |
| `GEMMA4_MODEL` | `gemma4` |

---

## 10. Scene 생성

Isaac Sim Python에서 실행해야 한다. 일반 Python에는 `pxr`/Isaac runtime이 없을 수 있다.

```bash
# l40s / Isaac container 안에서
cd /mnt/Trident-Twin-520d314
TWIN_HUB_URL=http://10.38.38.223:8765 \
  /isaac-sim/python.sh scripts/create_scene.py
```

생성 파일:

```text
stages/trident_lakehouse_twin_<YYYYMMDD_HHMM>.usda
```

현재 확인한 최신 파일:

```text
/mnt/Trident-Twin-520d314/stages/trident_lakehouse_twin_20260614_2234.usda
```

scene 내부 live-linked 결과 확인 예:

```bash
grep -n 'lakehouse.slot.icu_waveform_mixed_v1\|raw.icu_waveform_mixed_v1\|trident:table_role' \
  /mnt/Trident-Twin-520d314/stages/trident_lakehouse_twin_20260614_2234.usda | head
```

---

## 11. Isaac Sim / l40s runbook

현재 Isaac Sim은 `ssh netai@l40s`의 Docker container `isaac-sim-ICH-strongest`에서 실행한다.

중요 원칙:

- 다른 Isaac container/process는 건드리지 않는다.
- Digital Twin용으로는 **`isaac-sim-ICH-strongest`만** 확인/재시작한다.
- 가능하면 Docker container 자체 재시작보다 container 내부 `runheadless.sh`/`kit` stream process만 재시작한다.

상태 확인:

```bash
ssh netai@l40s 'bash -s' <<'REMOTE'
docker ps --filter name=isaac-sim-ICH-strongest --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
docker exec -u 1234 isaac-sim-ICH-strongest bash -lc \
  'ps -eo pid,cmd | grep -E "[/]isaac-sim/kit/kit|[r]unheadless.sh .*trident_lakehouse_twin" || true'
ss -ltnup | grep -E '10\.38\.38\.197:(49100|47998)' || true
REMOTE
```

Digital Twin 화면이 `Isaac Sim 스트리밍 서버에 연결 중… 10.38.38.197:49100`에서 오래 멈추면, 포트는 열려 있지만 WebRTC stream process가 stale 상태일 수 있다. 이때는 ICH container 안의 stream process만 재시작한다.

```bash
ssh netai@l40s 'bash -s' <<'REMOTE'
set -euo pipefail
CONTAINER=isaac-sim-ICH-strongest
SCENE=/mnt/Trident-Twin-520d314/stages/trident_lakehouse_twin_20260614_2234.usda
LOG=/tmp/trident-streaming-2234-restart.log

# Stop only the ICH stream process, not other containers.
docker exec -u 1234 "$CONTAINER" bash -lc '
  pkill -TERM -f "/isaac-sim/kit/kit .*trident_lakehouse_twin" || true
  pkill -TERM -f "runheadless.sh .*trident_lakehouse_twin" || true
  sleep 5
  pkill -KILL -f "/isaac-sim/kit/kit .*trident_lakehouse_twin" || true
  pkill -KILL -f "runheadless.sh .*trident_lakehouse_twin" || true
'

# Start latest scene stream.
docker exec -d -u 1234 "$CONTAINER" bash -lc \
  "cd /isaac-sim && ./runheadless.sh $SCENE \
    --/app/livestream/publicEndpointAddress=10.38.38.197 \
    --ext-folder /mnt/Trident-Twin-520d314/exts \
    --enable trident.twin > $LOG 2>&1"

# Wait for stream readiness.
for i in $(seq 1 120); do
  if docker exec -u 1234 "$CONTAINER" bash -lc "grep -q 'Full Streaming App is loaded' $LOG"; then
    echo "loaded after ${i}s"
    break
  fi
  sleep 1
  test "$i" != 120
 done

docker exec -u 1234 "$CONTAINER" bash -lc "grep -i 'Full Streaming App is loaded' $LOG | tail -1"
REMOTE
```

Portal에서 다시 볼 때는 브라우저 탭을 새로 열거나 강력 새로고침한다.

---

## 12. Build / deploy

### twin-hub image

```bash
docker build -f Dockerfile.twin-hub -t ich6648/trident-twin-hub:v0.1.2 .
docker push ich6648/trident-twin-hub:v0.1.2
```

### Portal image

Portal repo에서 빌드한다.

```bash
npm run build
docker build -t ich6648/trident-portal:v97.136 .
docker push ich6648/trident-portal:v97.136
```

### GitOps

실제 배포는 `SmartX-Team/TwinX-Ops`에서 PR/merge로 한다.

현재 반영 파일:

```text
argocd/trident/apps/trident-portal/install.yaml
argocd/trident/apps/trident-twin-hub/install.yaml
```

ArgoCD sync는 운영자가 수행한다.

---

## 13. Local validation

FastAPI 없이 fixture contract만 확인:

```bash
python3 twin-hub/test_stub.py
```

Python syntax 확인:

```bash
python3 -m py_compile \
  twin-hub/app.py \
  twin-hub/test_stub.py \
  scripts/create_scene.py \
  scripts/sync_scene_from_live.py
```

Fixture server로 HTTP 확인:

```bash
cd twin-hub
uvicorn app:app --reload --port 8765
curl http://localhost:8765/api/twin/health
curl http://localhost:8765/api/twin/cameras
curl http://localhost:8765/api/twin/entities | python3 -m json.tool | head
```

README link sanity:

```bash
python3 - <<'PY'
from pathlib import Path
import re
readme = Path('README.md').read_text(encoding='utf-8')
missing = []
for target in re.findall(r'!\[[^\]]*\]\(([^)]*)\)|\[[^\]]+\]\(([^)#][^)]*)\)', readme):
    t = next(x for x in target if x)
    if t.startswith(('http://', 'https://', 'mailto:')):
        continue
    if not Path(t).exists():
        missing.append(t)
print('missing:', missing)
PY
```

---

## 14. 남은 우선순위

1. **live stats-service secret 주입 정리**
   - `TRIDENT_STATS_BASE_URL`, Keycloak client secret을 OpenBao/ESO/K8s Secret으로 관리한다.
   - README/Git에는 secret 값을 남기지 않는다.

2. **namespace별 progress 정교화**
   - 현재 extension의 live box progress는 active raw event와 대표 pipeline 상태에 가깝다.
   - 목표는 namespace별 PROFILE→READY 상태를 독립적으로 표시하는 것이다.

3. **Portal Data Search → Lakehouse slot highlight 강화**
   - 검색 결과 entity id가 USD prim의 `trident:entity_id`와 더 안정적으로 매칭되게 한다.
   - 선택된 dataset/table의 Raw Bucket slot과 Lakehouse slot을 함께 highlight한다.

4. **Gemma4 Q&A context 확장**
   - 현재는 selected search candidate 중심이다.
   - 다음 단계는 table schema, sample metadata, lineage, quality score를 context로 함께 전달하는 것이다.

5. **scene regeneration cadence 정의**
   - raw dataset/table 구조가 바뀔 때 USD를 언제 재생성할지 정한다.
   - 계속 재생성하지 말고 명시적 운영 작업 또는 scheduled low-frequency job으로 분리한다.

---

## 15. 저장소 구조

```text
Trident-Twin/
├── README.md
├── Dockerfile.twin-hub
├── requirements-twin-hub.txt
├── data/
│   ├── twin_entities.json
│   └── mock_twin_events.json
├── docs/
│   ├── v10-design.md
│   ├── twin-architecture.md
│   ├── master-plan.md
│   ├── omniverse-twin-poc.md
│   └── site-plan-v2.png
├── exts/
│   └── trident.twin/
├── scripts/
│   ├── create_scene.py
│   ├── sync_scene_from_live.py
│   ├── live_sync.py
│   ├── open_latest_scene_streaming.py
│   └── capture_overview.py
├── stages/
└── twin-hub/
    ├── app.py
    ├── run_live.sh
    ├── test_stub.py
    └── README.md
```

문서 source of truth 우선순위:

1. `README.md` — 현재 운영/개발 기준
2. `scripts/create_scene.py` — 실제 scene layout/source of truth
3. `twin-hub/app.py` — HTTP contract/source mapping
4. `exts/trident.twin/` — Isaac runtime behavior
5. `docs/*.md` — 과거 설계/PoC 기록. 현재 구현과 다를 수 있음
