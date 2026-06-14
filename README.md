# Trident-Twin

**Trident Lakehouse Digital Twin — Portal `/digital-twin`에서 보는 데이터 레디니스/운영 상태 공간화 레이어**

마지막 업데이트: **2026-06-14**

Trident-Twin은 Trident Lakehouse를 3D로 예쁘게 꾸민 별도 제품이 아니다. Trident Portal 사용자가 “지금 어떤 데이터가 들어왔고, 어떤 단계까지 준비됐고, 어떤 워크로드로 넘길 수 있는지”를 빠르게 판단하도록 돕는 **읽기 중심(read-mostly) 디지털 트윈 viewer/event bridge**이다.

현재 안전하게 주장할 수 있는 범위는 다음과 같다.

- Portal의 **Digital Twin** 메뉴에서 Isaac/Omniverse WebRTC 화면을 임베드하고, 우측 패널에서 zone camera와 data search 탭을 제공한다.
- `twin-hub`가 fixture 또는 live stats-service 데이터를 `/api/twin/*` 계약으로 노출하고, Portal의 camera/highlight 클릭을 가벼운 command queue로 받는다.
- Isaac Sim extension `trident.twin`이 `twin-hub`를 폴링해 ingest/refinement 진행 상자를 USD stage 위에 생성·이동·제거하고, camera/highlight command를 반영한다.
- Trident의 source of truth는 Iceberg/Nessie/Redis/Milvus/PostgreSQL/stats-service/Portal이며, Omniverse는 그 상태를 공간적으로 투영한다.

명확한 non-goal:

- 폐루프 자동 제어(closed-loop control)가 완성된 시스템이라고 말하지 않는다.
- Omniverse를 catalog/storage/governance source of truth로 취급하지 않는다.
- 모든 Portal event가 현재 실시간 양방향 동기화된다고 과장하지 않는다.
- catalog/search/S3 전체 스캔을 frame 단위 또는 짧은 주기로 계속 돌리지 않는다. 무거운 조회는 TTL cache 또는 사용자 click/submit 시점에만 수행한다.

---

## 1. 관련 저장소와 역할

| 저장소 | 실제 역할 | Trident-Twin과의 연결 |
| --- | --- | --- |
| [`SmartX-Team/TwinX-Ops`](https://github.com/SmartX-Team/TwinX-Ops) | 실제 클러스터 배포 ArgoCD/GitOps repo | Portal/stats-service/Omniverse 배포값의 source of truth. Portal env에 `TWIN_HUB_URL`, `ISAAC_SIM_HOST`, `ISAAC_SIM_SIGNALING_PORT`가 선언되어 있다. |
| [`mj006648/Trident-Portal`](https://github.com/mj006648/Trident-Portal) | 실제 사용자 포탈 | `/digital-twin` 메뉴, Isaac WebRTC viewer, RBAC read-only overlay, ingest event forwarding을 가진다. |
| [`mj006648/Trident-Lakehouse`](https://github.com/mj006648/Trident-Lakehouse) | 실험/논문/phase 정리 repo | Phase 4를 viewer/event bridge 범위로 정의한다. Trident-Twin의 주장 범위도 여기에 맞춘다. |
| [`mj006648/Trident-Twin`](https://github.com/mj006648/Trident-Twin) | Digital Twin 구현 repo | USD scene, fixture data, FastAPI `twin-hub`, Isaac Sim extension, live sync scripts를 가진다. |

---

## 2. 현재 시스템 맥락

Trident Lakehouse의 현재 핵심 흐름은 다음과 같다.

```text
Portal /ingest
  → stats-service /spark/ingest
  → SparkApplication
  → trident_structurize.py + trident_index.py
  → Iceberg/Nessie + Redis + Milvus + PostgreSQL catalog/audit

Portal /search
  → stats-service /search, /search/filter, /search/filter/batch
  → Milvus semantic search + Redis evidence + deterministic Trino filter
  → Basket / Collection / CTAS / workload handoff 후보

Portal /digital-twin
  → /api/digital-twin/config + /api/digital-twin/health
  → Isaac Sim WebRTC stream
  → right panel: zone cameras + data search
  → click-triggered /api/digital-twin/camera, /highlight
  → twin-hub /api/twin/commands + optional /api/twin/entities polling
  → USD stage camera/highlight/live boxes
```

Lakehouse phase 문서 기준으로 Digital Twin은 **Phase 4: viewer/event bridge** 범위다. Workflow는 별도 **Phase 5: draft-only workflow planning** 범위이며, Twin이 workflow를 직접 실행하지 않는다.

---

## 3. 현재 구현 상태 요약

| 영역 | 현재 상태 | 근거 파일 |
| --- | --- | --- |
| Static USD scene | 구현됨. `scripts/create_scene.py`가 `stages/trident_lakehouse_twin_<timestamp>.usda`를 생성한다. | `scripts/create_scene.py`, `stages/` |
| Fixture contract | 구현됨. `data/twin_entities.json`, `data/mock_twin_events.json`로 오프라인 동작 가능. | `data/`, `twin-hub/test_stub.py` |
| `twin-hub` fixture mode | 구현됨. `TRIDENT_STATS_BASE_URL`이 없으면 fixture를 제공하고 camera/highlight command queue는 그대로 동작한다. | `twin-hub/app.py` |
| `twin-hub` live mode | 부분 구현됨. stats-service의 catalog/dataset/collection/audit/S3 list를 읽어 entity로 변환한다. | `twin-hub/app.py` |
| Keycloak token refresh | 코드상 구현됨. `TRIDENT_STATS_TOKEN` 또는 `TRIDENT_KC_*` 환경변수를 사용한다. | `twin-hub/app.py` |
| Isaac Sim extension | 구현됨. `/api/twin/commands`는 가볍게 상시 폴링하고, `Start Live`를 누른 경우에만 `/api/twin/entities`를 폴링해 pipeline gate/raw namespace box를 동기화한다. | `exts/trident.twin/` |
| Portal viewer embed | 구현됨. `/digital-twin`에서 Isaac stream을 띄우고 우측에 Zone Cameras/Data Search 탭을 제공한다. 권한 없는 사용자는 read-only overlay를 본다. | `Trident-Portal/src/app/(app)/digital-twin/page.tsx` |
| Portal ingest event hook | 구현됨. Portal event forwarding은 실패해도 ingest를 막지 않는 best-effort이고, `twin-hub`가 `/api/twin/ingest/*`로 active event를 보관한다. | Portal `/api/digital-twin/event`, `twin-hub/app.py` |
| GitOps deployment for twin-hub | 아직 없음. TwinX-Ops에는 Portal env만 있고 `twin-hub` Deployment/Service manifest는 없다. | `TwinX/argocd/trident/apps/trident-portal/install.yaml` |

---

## 4. 아키텍처

```text
                 ┌────────────────────────────────────────────┐
                 │ TwinX-Ops / ArgoCD                         │
                 │ - trident-portal image/env                  │
                 │ - trident-stats image/env                   │
                 │ - Omniverse / Isaac streaming manifests     │
                 └────────────────────────────────────────────┘
                                      │
                                      ▼
┌────────────────────────────┐   ┌────────────────────────────┐
│ Trident Portal             │   │ Trident stats-service       │
│ /digital-twin              │   │ /api/v1/catalog/overview    │
│ Isaac WebRTC viewer        │   │ /api/v1/catalog/datasets    │
│ RBAC read-only overlay     │   │ /collection                 │
│ camera/search command UI   │   │ /stats/audit, /stats/s3/*   │
└──────────────┬─────────────┘   └──────────────┬─────────────┘
               │                                 │
               │ WebRTC                          │ HTTP + optional Bearer token
               ▼                                 ▼
┌────────────────────────────┐   ┌────────────────────────────┐
│ Isaac Sim / Omniverse      │◀──│ twin-hub FastAPI            │
│ USD stage                  │   │ /api/twin/health            │
│ trident.twin extension     │   │ /api/twin/entities          │
│ live box/camera/highlight  │   │ /api/twin/state             │
└────────────────────────────┘   │ /api/twin/commands          │
                                 │ /api/twin/cameras           │
                                 │ /api/twin/events            │
                                 └────────────────────────────┘
```

### Source of truth 원칙

```text
상태의 원천:
  Iceberg / Nessie / Redis / Milvus / PostgreSQL / stats-service / Portal

Twin의 책임:
  readiness, metadata coverage, pipeline progress, ready bundle,
  search selection, workload delivery state를 USD/Viewer 위에 투영
```

### Runtime sync 정책: 계속 연동 vs 일회성 연동

랙을 줄이기 위해 Twin은 **가벼운 상시 채널**과 **무거운 click/submit 채널**을 분리한다.

| 구분 | 계속 연동할 것 | 일회성/클릭 시에만 할 것 | 계속 돌리지 않을 것 |
| --- | --- | --- | --- |
| Portal ↔ Isaac | WebRTC 화면 stream. 화면 전송 자체는 사용자 탭이 열려 있을 때 유지한다. | Zone camera 버튼 클릭 → `/api/digital-twin/camera` → `/api/twin/camera` command 1건 생성. | Portal이 camera 상태를 매 frame 재전송하지 않는다. |
| Portal ↔ Lakehouse search | 없음. 사용자가 입력하고 Search를 누른 때만 기존 `/api/search`를 호출한다. | 검색 결과 클릭 → `/api/digital-twin/highlight` → `/api/twin/highlight` command 1건 생성. | search 결과를 Digital Twin 탭에서 주기적으로 자동 새로고침하지 않는다. |
| twin-hub ↔ Isaac extension | `/api/twin/commands?since=<seq>`만 기본 1초 간격으로 가볍게 폴링한다. | command queue에 쌓인 camera/highlight만 적용한다. | command polling에서 catalog/S3/search 전체 조회를 하지 않는다. |
| Lakehouse entity sync | `Start Live`를 누른 경우에만 `/api/twin/entities`를 기본 5초 간격으로 폴링한다. twin-hub는 base entity를 기본 30초 TTL cache로 보호한다. | scene inventory refresh, USD 재생성, deployment image update는 명시적 작업/PR로 수행한다. | stats-service catalog/datasets/S3 list를 짧은 주기로 무한 스캔하지 않는다. |
| Ingest event | Portal event forwarding은 best-effort로 active event snapshot만 유지한다. | ingest 시작/단계 변경 이벤트가 발생한 시점에만 push한다. | event push 실패가 ingest pipeline을 막지 않는다. |

현재 l40s에서 확인한 runtime 기준:

```text
Isaac container: isaac-sim-ICH-strongest
Isaac public endpoint: 10.38.38.197:49100
Twin hub: http://10.38.38.96:8765 또는 host 내부 http://127.0.0.1:8765
Current health: {"status":"ok", "mode":"fixture", "live_configured": false}
```

즉 지금 바로 동작하는 것은 fixture + ingest active events + camera/highlight command bridge이며, live Lakehouse catalog 연동은 `TRIDENT_STATS_BASE_URL`/token을 배포값으로 넣어야 완성된다.

---

## 5. Portal 연동 상태

Portal의 Digital Twin 메뉴는 다음 코드 경로로 동작한다.

| Portal 경로 | 역할 |
| --- | --- |
| `src/components/TopNav.tsx` | `Digital Twin` 메뉴 노출 |
| `src/lib/rbac.ts` | 로그인된 Trident role은 viewer 접근 가능, `operator/admin/service`는 조작 가능 |
| `src/app/(app)/digital-twin/page.tsx` | `IsaacSimViewer`와 우측 Zone Cameras/Data Search 탭을 렌더링 |
| `src/app/api/digital-twin/config/route.ts` | `ISAAC_SIM_HOST`, `ISAAC_SIM_SIGNALING_PORT` 반환 |
| `src/app/api/digital-twin/health/route.ts` | `TWIN_HUB_URL/api/twin/health` proxy. 실패해도 fallback 상태를 반환해 viewer를 막지 않음 |
| `src/app/api/digital-twin/cameras/route.ts` | `TWIN_HUB_URL/api/twin/cameras` proxy. twin-hub 미도달 시 static camera preset fallback |
| `src/app/api/digital-twin/camera/route.ts` | zone camera 클릭을 `TWIN_HUB_URL/api/twin/camera`로 best-effort 전달 |
| `src/app/api/digital-twin/highlight/route.ts` | data search 결과 클릭을 `TWIN_HUB_URL/api/twin/highlight`로 best-effort 전달 |
| `src/components/IsaacSimViewer.tsx` | 권한 없을 때 viewer 위에 read-only overlay 표시 |
| `src/components/digital-twin/AppStream.tsx` | NVIDIA Omniverse WebRTC direct stream 연결 |
| `src/app/api/digital-twin/event/route.ts` | ingest event를 `TWIN_HUB_URL/api/twin/ingest/event`로 best-effort forwarding |

현재 TwinX-Ops의 Portal 배포값:

```yaml
TWIN_HUB_URL:              http://10.38.38.96:8765
ISAAC_SIM_HOST:            10.38.38.197
ISAAC_SIM_SIGNALING_PORT:  49100
STATS_URL:                 http://trident-stats.trident.svc.cluster.local
```

주의할 점:

- Portal의 `/api/digital-twin/event`, `/camera`, `/highlight`는 실패해도 Portal의 기본 viewer/search 흐름을 막지 않는다.
- 현재 l40s의 `twin-hub`는 `live_configured=false` fixture mode다. 실제 Lakehouse catalog를 계속 보려면 배포 환경에 `TRIDENT_STATS_BASE_URL`과 필요한 token/KC secret을 추가해야 한다.
- 검색은 Digital Twin 탭에서 계속 polling하지 않고, 사용자가 Search를 누를 때 기존 Portal `/api/search`를 호출한 뒤 선택 결과만 highlight command로 보낸다.

---

## 6. `twin-hub` HTTP contract

`twin-hub`는 FastAPI adapter이다. 목적은 Isaac extension과 Portal-facing helper가 동일한 `/api/twin/*` schema를 보게 하는 것이다.

### 엔드포인트

| Method | Path | 현재 동작 |
| --- | --- | --- |
| `GET` | `/api/twin/health` | fixture/live/degraded 상태와 live dataset count를 반환 |
| `GET` | `/api/twin/cameras` | Portal Zone Cameras 탭이 보여줄 preset 목록 반환 |
| `POST` | `/api/twin/camera` | camera switch command를 queue에 append |
| `POST` | `/api/twin/highlight` | search result/entity highlight command를 queue에 append |
| `GET` | `/api/twin/commands?since=<seq>` | Isaac extension이 아직 처리하지 않은 camera/highlight command 반환 |
| `POST` | `/api/twin/ingest/event` | Portal ingest event를 active event snapshot으로 저장 |
| `GET` | `/api/twin/ingest/active` | 현재 active ingest namespace/event 반환 |
| `DELETE` | `/api/twin/ingest/clear` | active ingest event snapshot 초기화 |
| `GET` | `/api/twin/entities` | fixture 또는 live entity 목록 반환. base entity는 기본 30초 TTL cache 적용 |
| `GET` | `/api/twin/state` | entity를 `trident:*` attribute snapshot으로 reduce |
| `GET` | `/api/twin/events?since=<ts>` | fixture timeline event 반환. live mode에서는 per-second event를 조작해 만들지 않음 |
| `POST` | `/api/twin/live/start` | Isaac container 안에서 `scripts/live_sync.py` 실행 시도 |
| `POST` | `/api/twin/live/stop` | 위 live sync process 중지 |
| `GET` | `/api/twin/live/status` | live sync process 상태 반환 |

### Fixture mode

`TRIDENT_STATS_BASE_URL`이 없으면 checked-in fixture를 그대로 제공한다.

```bash
cd twin-hub
uvicorn app:app --reload --port 8765

curl http://localhost:8765/api/twin/health
curl http://localhost:8765/api/twin/entities
curl http://localhost:8765/api/twin/state
```

### Live stats-service mode

```bash
cd twin-hub
TRIDENT_STATS_BASE_URL=http://10.234.33.83 \
uvicorn app:app --host 0.0.0.0 --port 8765
```

stats-service가 Bearer token을 요구하면 둘 중 하나를 사용한다.

```bash
# 1) 정적 token
export TRIDENT_STATS_TOKEN='<access-token>'

# 2) Keycloak client_credentials 자동 갱신
export TRIDENT_KC_URL='http://10.38.38.220:8080/realms/trident/protocol/openid-connect/token'
export TRIDENT_KC_CLIENT_ID='trident-baseline-runner'
export TRIDENT_KC_CLIENT_SECRET='<secret-from-secret-store>'
```

Secret은 README, Git, shell history에 남기지 않는다.

### Live source mapping

| stats-service source | Twin entity |
| --- | --- |
| `/api/v1/catalog/overview` | pipeline runs, dataset overview, integrity summary |
| `/api/v1/catalog/datasets?limit=100` | `iceberg_table` inventory entity |
| `/collection` | `ready_bundle` entity |
| `/stats/audit` | pipeline gate status, raw namespace audit/readiness |
| `/stats/s3/list?bucket=trident-raw...` | `raw_bucket` object/file count |

---

## 7. Entity schema

`twin-hub`는 다음 entity type을 중심으로 반환한다.

| Entity type | 의미 | 주 사용처 |
| --- | --- | --- |
| `raw_bucket` | S3 raw namespace 상태 | Raw Bucket zone, live box 생성 조건 |
| `pipeline_operation` | INGEST/STRUCT/INDEX/EMBED/AUDIT 5단계 gate 상태 | Accumulation/Pipeline zone |
| `iceberg_table` | Lakehouse에 등록된 table/data product | Lakehouse inventory |
| `ready_bundle` | Basket/Collection/CTAS 후보 또는 materialized bundle | Staging/Showcase |
| `search_highlight` | Portal search selection 또는 후보 강조 | Search counter |
| `workload_delivery_package` | AI/HPC/HPDA handoff package | Delivery zone |
| `operator` | viewer/operator control anchor | Control tower |

USD prim과 state snapshot에는 가능한 한 `trident:*` custom attribute를 붙인다.

```text
trident:entity_id
trident:entity_type
trident:name
trident:zone
trident:stage
trident:namespace
trident:component
trident:readiness_score
trident:quality_score
trident:semantic_ready
trident:location_ready
trident:policy_ready
trident:last_event
```

---

## 8. Isaac Sim extension: `trident.twin`

Extension 위치:

```text
exts/trident.twin/trident/twin/extension.py
```

Extension Manager에서 다음 search path를 추가한다.

```text
Extensions > Settings > Extension Search Paths
  + /mnt/Trident-Twin-520d314/exts
```

그 후 `trident.twin`을 활성화한다.

UI:

| 항목 | 의미 |
| --- | --- |
| `twin-hub` | polling 대상 base URL. 컨테이너 기본값 `http://172.17.0.1:8765` |
| `Interval (s)` | polling 간격. 최소 2초 |
| `Start Live` | Kit update loop에서 무거운 `/api/twin/entities` polling 시작 |
| `Stop` | entity polling과 live boxes를 중지/초기화. camera/highlight command polling은 extension 활성 상태에서 유지 |

환경변수:

| 변수 | 기본값 | 설명 |
| --- | --- | --- |
| `TWIN_HUB_URL` | `http://172.17.0.1:8765` | Isaac container에서 host twin-hub로 접근하는 기본 base URL |
| `TWIN_POLL_INTERVAL` | `5` | live entity polling interval seconds. `Start Live` 이후에만 사용 |
| `TWIN_COMMAND_POLL_INTERVAL` | `1` | camera/highlight command polling interval seconds. extension 활성화 중 가볍게 상시 사용 |

현재 live/command 로직:

1. extension이 활성화되면 `/api/twin/commands?since=<seq>`를 기본 1초 간격으로 폴링한다.
2. camera command는 active viewport camera를 `/World/Cameras/*` preset으로 전환한다.
3. highlight command는 `trident:entity_id`가 일치하는 prim subtree의 displayColor를 cyan 계열로 바꾼다.
4. 사용자가 `Start Live`를 누른 경우에만 `/api/twin/entities`에서 `pipeline_operation` entity를 읽어 5개 gate status를 만든다.
5. `raw_bucket` entity 중 active event가 있는 namespace를 box로 만들고, gate가 진행될수록 `/World/LiveSync/Box_<namespace>`가 다음 x 위치로 이동하며 badge가 붙는다.
6. AUDIT gate가 완료되면 Lakehouse 방향으로 이동 후 제거한다.

현재 한계:

- gate status는 namespace별 독립 progress가 아니라 `twin-hub`가 집계한 대표 상태에 가깝다.
- camera/highlight command는 queue 기반 best-effort다. Isaac extension이 비활성/미로드 상태면 command는 twin-hub에 쌓이지만 화면에는 반영되지 않는다.
- l40s runtime은 현재 fixture mode이므로 live Lakehouse catalog entity는 `TRIDENT_STATS_BASE_URL`/token 배포 전까지 완전한 실시간 데이터가 아니다.

---

## 9. USD scene 생성

Isaac Sim Python에서 실행해야 한다. 일반 Python에는 `pxr`/Isaac runtime이 없을 수 있다.

```bash
# Isaac Sim 컨테이너/호스트 안에서
cd /mnt/Trident-Twin-520d314
/isaac-sim/python.sh scripts/create_scene.py
```

생성 파일:

```text
stages/trident_lakehouse_twin_<YYYYMMDD_HHMM>.usda
```

Isaac Sim에서 열기:

```text
File > Open > /mnt/Trident-Twin-520d314/stages/trident_lakehouse_twin_<timestamp>.usda
```

Live stats-service 기반으로 scene inventory entity id를 먼저 맞추고 싶으면:

```bash
TRIDENT_STATS_BASE_URL=http://10.234.33.83 \
TRIDENT_STATS_TOKEN='<access-token>' \
python3 scripts/sync_scene_from_live.py

# 그 다음 Isaac Sim Python으로 USD 재생성
/isaac-sim/python.sh scripts/create_scene.py
```

---

## 10. Scene layout

현재 README 기준 scene은 `docs/v10-design.md`와 `scripts/create_scene.py`의 구현을 우선한다.

| Zone | 위치/역할 | 현재 구현 |
| --- | --- | --- |
| Control Tower | 전체 조망/운영자 anchor | 정적 관제탑, Portal monitor mirror는 미구현 |
| Truck Yard | 외부 raw data 유입 표현 | 트럭 + inbound conveyor |
| Raw Bucket | tag 없는 raw object/namespace | namespace별 raw box 더미 |
| Refinement Pipeline | INGEST/STRUCT/INDEX/EMBED/AUDIT | main/express belt + 5 station + live box overlay |
| Lakehouse Inventory | Iceberg/Nessie catalog table 보관 | storage table grid + readiness crates |
| Staging/Showcase | 자주 쓰는 bundle/display | display cabinet + ready bundle props |
| Search Counter | Portal search/readiness decision | search desk + indicator lights + static roles |
| Delivery | AI/HPC/HPDA handoff | Big consolidation table + 3 outgoing belts + trucks |

씬 스크린샷:

| 정상 90도 | 사선 45도 |
|:---:|:---:|
| ![top90](docs/screenshots/overview_top90_v3.png) | ![top45](docs/screenshots/overview_top45_v3.png) |

존별 스크린샷:

| Zone 1 — Truck Yard | Zone 2 — Raw Bucket |
|:---:|:---:|
| ![zone1](docs/screenshots/zone_01_truck_yard_v3.png) | ![zone2](docs/screenshots/zone_02_raw_bucket_v3.png) |

| Zone 3 — Accumulation | Zone 4 — Lakehouse |
|:---:|:---:|
| ![zone3](docs/screenshots/zone_03_accumulation_v3.png) | ![zone4](docs/screenshots/zone_04_lakehouse_v3.png) |

| Zone 5 — Search | Zone 6 — Delivery |
|:---:|:---:|
| ![zone5](docs/screenshots/zone_05_search_v3.png) | ![zone6](docs/screenshots/zone_06_delivery_v3.png) |

| Zone 7 — Control Tower |
|:---:|
| ![zone7](docs/screenshots/zone_07_tower_v3.png) |

Top-view 설계도:

![site-plan](docs/site-plan-v2.png)

---

## 11. 실제 클러스터 runbook

현재 repo evidence 기준 운영값:

| 항목 | 값/설명 |
| --- | --- |
| Portal service | `http://10.38.38.217` |
| Portal image | `ich6648/trident-portal:v97.133` |
| stats-service image | `ich6648/trident-stats:v6.37` |
| Portal → stats-service | `http://trident-stats.trident.svc.cluster.local` |
| Portal → twin-hub | `http://10.38.38.96:8765` |
| Portal → Isaac signaling | `10.38.38.197:49100` |
| Keycloak realm | `http://10.38.38.220:8080/realms/trident` |

`twin-hub`를 l40s/Isaac 환경에서 수동 실행하는 현재 방식:

```bash
ssh netai@l40s "docker exec -d isaac-sim-ICH-strongest bash -c '
cd /mnt/Trident-Twin-520d314/twin-hub
TRIDENT_STATS_BASE_URL=http://10.234.33.83 \
TRIDENT_KC_URL=http://10.38.38.220:8080/realms/trident/protocol/openid-connect/token \
TRIDENT_KC_CLIENT_ID=trident-baseline-runner \
TRIDENT_KC_CLIENT_SECRET=<secret> \
/isaac-sim/kit/python/bin/uvicorn app:app \
  --host 0.0.0.0 --port 8765 --log-level info > /tmp/twin-hub.log 2>&1
'"
```

확인:

```bash
ssh netai@l40s "docker exec isaac-sim-ICH-strongest bash -c 'tail -40 /tmp/twin-hub.log'"
ssh netai@l40s "docker exec isaac-sim-ICH-strongest bash -c 'python3 - <<PY
import json, urllib.request
payload = json.load(urllib.request.urlopen(\"http://localhost:8765/api/twin/health\"))
print(payload)
PY'"
```

주의:

- `twin-hub/run_live.sh`는 일반 `uvicorn`을 호출한다. Isaac container에서는 PATH에 따라 `/isaac-sim/kit/python/bin/uvicorn` 절대경로가 필요할 수 있다.
- GitOps로 운영하려면 TwinX-Ops에 `twin-hub` Deployment/Service/Secret reference를 추가해야 한다. 현재는 Portal env만 GitOps에 있다.

---

## 12. 로컬 검증

FastAPI/uvicorn 없이 fixture contract만 확인:

```bash
python3 twin-hub/test_stub.py
```

Python syntax 확인:

```bash
python3 -m py_compile twin-hub/app.py twin-hub/test_stub.py scripts/sync_scene_from_live.py
```

Fixture server로 HTTP 확인:

```bash
cd twin-hub
uvicorn app:app --reload --port 8765
curl http://localhost:8765/api/twin/health
curl http://localhost:8765/api/twin/entities | python3 -m json.tool | head
```

Markdown image/link sanity:

```bash
python3 - <<'PY'
from pathlib import Path
import re
readme = Path('README.md').read_text(encoding='utf-8')
missing = []
for target in re.findall(r'\]\(([^)#][^)]*)\)', readme):
    if target.startswith(('http://', 'https://', 'mailto:')):
        continue
    path = Path(target)
    if not path.exists():
        missing.append(target)
for target in re.findall(r'!\[[^\]]*\]\(([^)]*)\)', readme):
    path = Path(target)
    if not path.exists():
        missing.append(target)
print('missing:', missing)
PY
```

---

## 13. 오늘 이후 우선순위

1. **Portal event contract 정리**
   - 선택 A: `twin-hub`에 `POST /api/twin/ingest/event`를 추가한다.
   - 선택 B: Portal event hook을 제거/비활성화하고 polling-only로 명확히 둔다.

2. **twin-hub 배포 방식 결정**
   - 현재: l40s/Isaac host에서 수동 실행.
   - 목표: TwinX-Ops에 Deployment/Service/Secret reference를 추가해 GitOps로 관리.

3. **namespace별 progress 모델 개선**
   - 현재 extension은 gate status를 대표 집계로 읽는다.
   - 목표는 raw namespace마다 INGEST→STRUCT→INDEX→EMBED→AUDIT 진행을 독립적으로 보여주는 것이다.

4. **Portal search selection → USD highlight**
   - `/search` 후보 클릭 또는 Basket/Collection 선택을 `entity_id`로 twin-hub에 전달.
   - Isaac extension은 해당 USD prim을 highlight한다.

5. **주장 범위 유지**
   - Phase 4는 viewer/event bridge.
   - 자동 실행, 폐루프 제어, full simulation은 Phase 6+ 후보로 분리한다.

---

## 14. 저장소 구조

```text
Trident-Twin/
├── README.md
├── data/
│   ├── twin_entities.json          # fixture entity contract
│   └── mock_twin_events.json       # fixture replay timeline
├── docs/
│   ├── v10-design.md               # current scene layout reference
│   ├── twin-architecture.md        # older architecture note
│   ├── master-plan.md              # older plan; partially stale
│   ├── site-plan-v2.png
│   └── screenshots/
├── exts/
│   └── trident.twin/               # Isaac/Omniverse Kit extension
├── scripts/
│   ├── create_scene.py             # USD scene generator
│   ├── sync_scene_from_live.py      # stats-service → create_scene inventory sync
│   ├── live_sync.py                # standalone USD live sync/reference script
│   └── render_topdown_diagrams.py
├── stages/                         # generated USD stages
└── twin-hub/
    ├── app.py                      # FastAPI fixture/live adapter
    ├── run_live.sh                 # live-mode helper
    ├── test_stub.py                # stdlib fixture contract smoke test
    └── README.md
```

문서 source of truth 우선순위:

1. `README.md` — 현재 운영/개발 기준
2. `docs/v10-design.md` — 현재 scene layout 기준
3. `twin-hub/README.md` — hub-specific quick reference
4. `docs/master-plan.md`, `docs/omniverse-twin-poc.md`, `docs/twin-architecture.md` — 과거 설계/PoC 기록. 현재 구현과 다를 수 있음
