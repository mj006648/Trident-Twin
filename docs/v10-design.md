# Trident-Twin v10 Design (Implemented)

> **이 문서는 현재 `scripts/create_scene.py` (v10 layout) 의 구현 상태를
> 정확히 기술한다.** 원본 설계안(이전 master-plan)에서 일부 zone(Audit Gate,
> Catalog Office)이 제거되었고, Lobby와 Search Counter가 단일 plaza로
> 통합되었으며, 3개의 dock 테이블이 한 개의 큰 consolidation table로
> 합쳐졌다. 좌표 단위는 모두 미터.

---

## 1. 핵심 공간 구성

| 공간 | 역할 | 박스 상태 | 구현 상태 |
| --- | --- | --- | --- |
| ① Raw Bucket 창고 | 원시 데이터 무가공 적재 | 민짜 갈색 박스 (60개) | ✅ |
| ② Lakehouse 저장동 | 메타데이터가 부여된 데이터의 정식 보관소 | 흰 Iceberg 박스 + 보라 라벨 + 빨강 카드 + 상태 LED, 테이블 위 적재 | ✅ |
| ③ Showcase 진열장 | 자주 쓰는 박스만 꺼내둔 핫존 | 라벨 박스 + 글래스 캐비닛 + 천장 전구 + 인기도 별점 | ✅ |

> Lakehouse는 모든 정제 데이터가 보관되는 메인 창고이며, 진열장은 그중 사용
> 빈도가 높은 데이터만 별도로 노출하는 공간이다. 두 건물은 Y축으로
> 나란히(LH cy=0, SC cy=+22) 배치되어 있다.

---

## 2. 전체 데이터 흐름

### 메인 데이터 흐름

1. **[트럭 진입]** — Inbound truck (4 wheels, cab west / trailer rear east at X=-18) 정차
2. **[인바운드 컨베이어]** — 5.6m 길이로 트럭 후미 → Raw 서벽 (Y=0)
3. **[① Raw Bucket 창고]** — 갈색 박스 60개 dense 적재 (내부 belt 없음, 순수 storage)
4. **[Pipeline (Zone 3)]** — Raw 동벽에서 동시에 시작되는 **두 평행 belt** (Main Y=-0.7 + Express Y=+0.7, 둘 다 width 1.0). 5개 스테이션이 두 belt 위를 모두 덮음.
5. **[Pipeline → Lakehouse]** — 두 belt가 X=+20.4에서 Y bend로 Y=0 단일 라인으로 합류, LH 서벽으로 진입.
6. **[② Lakehouse 저장동]** — Iceberg 박스가 5×4 storage table 그리드(총 20 테이블, 약 60 박스)에 보관됨. 데모용 lineage 광선 3 줄.
7. **[Lakehouse → Showcase Promotion belt]** — 핑크 프레임의 Y축 belt가 LH 북벽(Y=+6)에서 SC 남벽(Y=+16)까지 X=+29에서 직행.
8. **[③ Showcase 진열장]** — 7개 living-room 스타일 글래스 캐비닛 (북벽 2 + 중간 freestanding 3 + 남벽 2). 각 캐비닛은 3 선반 × 4 박스 + 스포트라이트.
9. **[Lobby + Search Counter]** — LH/SC 사이 corridor(Y=+10)에서 사용자가 검색 → Milvus(보라) → LLM(주황) → Redis(빨강) 표시등 순차 점등.
10. **[LH/SC → Big Consolidation Table]** — LH 동벽에서 X belt + Y bend로 Big Table 남쪽, SC 동벽에서 X belt + Y bend로 Big Table 북쪽 진입.
11. **[Big Table → Delivery Docks]** — Big Table 동벽에서 **3개의 직선 belt** (Y bend 없음)가 각 트럭으로 직진.
12. **[Delivery Docks]** — 3대 트럭이 후미(open rear)를 서쪽 Big Table 쪽으로 향한 채 주차 (AI 녹색, HPC 회색, HPDA 파랑). 각 4 wheels.

### 부가 흐름

- **사용자 진입**: 사용자가 Lobby plaza에 등장 → Search Counter 단말기 사용 → 데이터가 LH 또는 SC에서 Big Table로 호출 → 트럭으로 배송.
- **계보 시각화**: Lakehouse 내부에 3개의 데모 광선만 존재 (table 단위 흰색, 컬럼 단위 보라 점선, 영향도 노랑). 풀-fledged 광선 네트워크는 미구현.

---

## 3. 구역별 세부 설계 (v10 좌표)

### Zone 0+7 (MERGED) — Lobby & Search Counter

- **위치**: 중심 (+44, +10), plaza 7×7m. LH 동벽(+37.5)과 Big Table(+50) 사이 corridor에 배치, 중간 라인 Y=+10.
- **구성**:
  - 사각 plaza (white panel)
  - 리셉션 데스크 + 모니터
  - 검색 카운터 데스크 + 단말기 + 3-단 표시등 패널 (Milvus 보라 / LLM 주황 / Redis 빨강)
  - 5 마네킹: admin(금), researcher(흰), operator(파랑), viewer(회색), librarian(파랑)
- **제거된 요소**: 출입 게이트 / JWT 라이트 / 권한 거부 시 빨간 X 등 Keycloak 인터랙티브 요소 — 미구현.
- **대응 백엔드 (예정)**: Keycloak realm trident, JWT claims, PostgreSQL access_policies, Phase 3 Semantic + SQL Filter + Storage Search.

### Zone 1 — Inbound Truck Yard

- **위치**: 중심 (-22, 0), asphalt pad 14×8m + 노란 stripe 2 줄.
- **구성**: cab(빨강) + trailer(흰색) + 4 wheels (1 trailer axle + 1 cab axle), 트럭 후미 X=-18 (Raw 서벽 방향).
- **흐름**: 트레일러 후미 → 인바운드 belt 5.6m → Raw 창고.
- **대응 백엔드**: 외부 시스템 → S3 PUT.

### Zone 2 — Raw Bucket 창고 (Bronze)

- **위치**: 중심 (-4, 0), 17×12×6m. 컬러 floor pad = 갈색.
- **외형**: 강철 프레임 + 반투명 청색 글래스 벽, 천장 cross beam 3 줄.
- **내용물**: 60개 갈색 무지 박스 (남벽 라인 19개 + 북벽 라인 16개 + 중간 cluster 18개 + 중앙 통로 산개 7개). 일부 2-3단 stack.
- **내부 belt 없음** (Data Swamp 표현).
- **대응 백엔드**: Ceph S3 Raw Bucket.

### Zone 3 — Trident Pipeline Line (이중 공정 라인)

두 평행 belt가 Raw 동벽(X=+4.7)에서 시작해 LH 서벽(X=+20.4)까지 동시에 운행한다.

| 라인 | 위치 | 너비 | 용도 |
| :--- | :--- | :--- | :--- |
| **Main (Full Mode)** | Y=-0.7, 검은 belt + 주황 프레임 | 1.0m | 신규 데이터셋 최초 구조화 |
| **Express (Delta Mode)** | Y=+0.7, 어두운 회색 belt + 주황 프레임 | 1.0m | 기존 데이터셋 증분 추가 |

5개 스테이션이 두 belt 모두를 덮는 canopy 구조 (cy=0, sy=3.0):

- **3-1 Probing Arm** (X=+7) — 노란 로봇팔 + 빨간 스캐너 빔 + JSON/CSV/TSV 포맷 아이콘 3개.
- **3-2 AI Architect Desk** (X=+10) — 책상 + 모니터 + 홀로그램 스키마 트리 (큐브 6개).
- **3-3 Iceberg Packaging** (X=+13) — 아치 + 5개 노즐 + 눈송이 엠블럼 + 스파크 ember.
- **3-4 Milvus Labeler** (X=+16) — 보라색 column + arm + stamp head + 홀로그램 라벨.
- **3-5 Redis Indexer** (X=+19) — 빨간 dispenser + chute + 카드 샘플 + LED 표시등.

**Pipeline → Lakehouse**: 두 belt가 X=+20.4에서 각각 Y bend로 Y=0 합류 → LH 서벽 진입.

> **미구현**: file_registry 바이패스, Delta Mode 작은 큐브 박스 시각화.

### Zone 3.5 — ~~Integrity Audit Gate~~ ❌ 제거됨

원본 설계에 있었으나 v10에서 제거. Pipeline에서 LH로 직접 연결.

### Zone 4 — Lakehouse 저장동 (Silver Storage)

- **위치**: 중심 (+29, 0), 17×12×6m. 컬러 floor pad = teal.
- **외형**: 강철 프레임 + 반투명 녹색 글래스 벽, 천장 cross beam.
- **내부 구성**: **5 cols × 4 rows = 20 storage tables** 그리드. 각 테이블 (table_top 갈색 + 4 강철 다리) 위에 2-3개 Iceberg 박스.
- **박스 외형**: 흰색 본체 + 보라 측면 라벨 (Milvus) + 빨강 상단 카드 (Redis) + 모서리 LED (초록 / 노랑 / 빨강 deterministic).
- **계보 광선 데모**: 3 줄만 — 흰색 가는 줄 (table 단위), 보라 점선 (컬럼 단위), 노란 굵은 줄 (영향도).
- **내부 컨베이어 없음** (사용자 요청).
- **대응 백엔드**: Iceberg + Nessie, PostgreSQL catalog.datasets, lineage.nodes/edges.

> **변경점**: 원본의 "통로식 선반(aisle shelves)" → 단순 storage table로 단순화.

### Zone 5 — Showcase 진열장 (Hot Display)

- **위치**: 중심 (+29, +22), 17×12×6m. 컬러 floor pad = gold.
- **외형**: 강철 프레임 + 반투명 금색 글래스 벽.
- **내부 구성**: **7개 living-room 스타일 글래스 캐비닛** (북벽 2 + 중간 freestanding 3 + 남벽 2). 각 캐비닛 4.5×0.8×2.4m.
  - 나무 base + 나무 crown trim + 4 corner posts + 2 vertical dividers
  - 글래스 front (반투명)
  - 3 horizontal 선반 × 각 4 박스 = 12 박스/캐비닛 (총 ~84 박스)
  - 천장 전구 3개 (노랑)
  - front plaque (금색) + 인기도 별점 큐브
- **대응 백엔드**: Redis hot key, Dataset Basket, access_audit 로그.

> **변경점**: 원본의 "스포트라이트 + 받침대 + 박물관 윈도우" → 거실 진열장 furniture로 변경 (사용자 요청).

### Zone 6 — ~~Catalog Office~~ ❌ 제거됨

원본 설계에 있었으나 v10에서 제거. Lineage / RBAC / Quality SLO 모니터는 Trident Portal에서 별도 표시 예정.

### Zone 7 — Search Counter

> **Zone 0 (Lobby)와 통합됨** → 위 Zone 0+7 참조.

### Zone 8 — Delivery Docks (출고 하역장)

#### Big Consolidation Table (Zone 8 입구)

- **위치**: 중심 (+52, +10), 4m(X) × 11m(Y) × 0.85m(Z 테이블 상판). 컬러 floor pad = violet (Delivery zone).
- **외형**: 4 다리 + 갈색 상판 + 남쪽 가장자리 cold rail(파랑) + 북쪽 가장자리 hot rail(빨강).
- **상판 위 8개 sample 박스** (Iceberg, 다양한 LED).
- **역할**: LH belt + SC belt의 합류점이자 3 트럭 dispatch 분기점.

#### 들어오는 belt (2 개)

- **LH belt (cold, 파랑 프레임)**: X belt (+37.5→+52, Y=0) → Y bend (Y=0→+4.5, X=+52) → 테이블 남쪽 진입.
- **SC belt (hot, 빨강 프레임)**: X belt (+37.5→+52, Y=+22) → Y bend (Y=+22→+15.5, X=+52) → 테이블 북쪽 진입.

#### 나가는 belt (3 개, 모두 일직선)

| Belt | Y | 출구 | 도착 |
| :--- | :--- | :--- | :--- |
| AI dock | Y=+6 | (X=+54, Y=+6) | (X=+61.5, Y=+6) |
| HPC dock | Y=+10 | (X=+54, Y=+10) | (X=+61.5, Y=+10) |
| HPDA dock | Y=+14 | (X=+54, Y=+14) | (X=+61.5, Y=+14) |

#### Dock 차량

| 차량 | 위치 | 외형 | 박스 변형 |
| :--- | :--- | :--- | :--- |
| **AI Truck** | rear at (+62, +6) | NVIDIA green + accent stripe | 일반 박스 (URI 두루마리 미구현) |
| **HPC Van** | rear at (+62, +10) | gray + accent | 일반 박스 (폴더 구조 미구현) |
| **HPDA Van** | rear at (+62, +14) | dark blue + light blue accent | 일반 박스 (가상 테이블 미구현) |

- 모든 차량 동향(cab 동쪽, open rear 서쪽 = Big Table 방향).
- 4 wheels (1 body axle + 1 cab axle).
- 워크로드별 박스 변형(두루마리/폴더/테이블)은 **미구현**.

### Zone 9 — Twin Control Tower (관제탑)

- **위치**: (-22, -13). 컬러 floor pad = 남색.
- **외형**: concrete 베이스 + 9m 강철 shaft + glass 전망 데크 + 안테나 + 빨간 LED 팁.
- **내부**: operator chair + desk (전망데크 안).
- **역할**: 전체 facility 조망. Portal/WebRTC 연동은 미구현.

---

## 4. 박스 외형의 진화 단계 (v10 실측)

| 단계 | 위치 | 외형 |
| --- | --- | --- |
| 1 | 트럭 내부 | (가시화 안 됨) |
| 2 | Raw 창고 | 갈색 무지 큐브 (60개) |
| 3 | Pipeline 통과 후 | (별도 변형 없음, Dataset Package만 색이 변함) |
| 4 | Lakehouse 저장 | 흰 Iceberg + 보라 라벨 + 빨강 카드 + LED |
| 5 | Showcase 캐비닛 안 | 위 + 글래스 캐비닛 + 천장 전구 + 인기도 별점 |
| 6 | Big Table 위 | 위와 동일 박스가 적재됨 |
| 7 | 트럭 적재 | 일반 박스 (워크로드별 변형 미구현) |

---

## 5. 사용자 아바타 시스템 (현재 미실현 / 정적 마네킹만)

| 단계 | 동작 | 시각 표현 | 구현 |
| :---: | --- | --- | :---: |
| 1 | 로그인 | 정문 게이트 통과 + JWT LED | ❌ 미구현 |
| 2 | 시설 진입 | 머리 위 출입증 카드 표시 | ❌ 미구현 |
| 3 | 검색 수행 | 카운터 단말기 사용 | ⚠️ 정적 |
| 4 | 데이터 호출 | 박스가 부유 이동 | ❌ 미구현 |
| 5 | 데이터 출고 | 아바타가 박스 들고 dock 이동 | ❌ 미구현 |
| 6 | 권한 거부 | 빨간 X + 튕겨남 | ❌ 미구현 |
| 7 | 로그아웃 | 정문 퇴장 | ❌ 미구현 |

**현재 상태**: Lobby plaza에 5 마네킹(admin/researcher/operator/viewer/librarian)이 정적으로 배치되어 있음. role color 표시. Keycloak/JWT/access_policy 연동은 Phase 6+에서 처리.

---

## 6. 분기 및 예외 경로 요약 (v10)

| 분기 상황 | 조건 | 시각 표현 | 구현 상태 |
| :--- | :--- | :--- | :---: |
| Full Mode | 신규 데이터셋 | Main belt 사용, 5 스테이션 풀 코스 | ✅ |
| Delta Mode | 기존 데이터셋 증분 | Express belt 사용 | ⚠️ 라인 있음, 박스 변형/동작 없음 |
| file_registry 바이패스 | URI 컬럼 미존재 | Architect / Iceberg 건너뛰기 | ❌ 미구현 |
| Integrity Pass / Fail | 정합성 검증 | 녹/적 점등 + 폐기 분기 | ❌ Audit Gate 제거 |
| 권한 거부 | RBAC 위반 | 빨간 X + 차단 | ❌ 미구현 |

---

## 7. v10 좌표 cheat-sheet

```
Y=+29 ─── Showcase 북벽 (캐비닛 row N)
                          ⋯
Y=+16 ─── SC south wall ────────────┐
                                     │ promotion belt (X=+29, 10m)
Y=+15.5 ─ Big Table north edge ──── │
Y=+14 ─── HPDA truck ───────────────│
Y=+10 ─── HPC truck = Big Table = Lobby+SC plaza  ★ main line ★
Y=+6 ──── AI truck = LH north wall ─┘
                          ⋯
Y=0 ───── LH center / Pipeline main belt main flow
Y=-0.7 ── Pipeline main belt
Y=+0.7 ── Pipeline express belt
                          ⋯
Y=-13 ─── Control Tower

X=-22 ─── Control Tower / Inbound truck cab
X=-18 ─── Inbound truck rear
X=-12.5 ─ Raw west wall (5.6m inbound belt entry)
X=-4 ──── Raw center
X=+4.7 ── Raw east wall, Main/Express belt start
X=+7~+19 5 pipeline stations (every 3m)
X=+20.4 ─ Y-bend converge to Y=0
X=+20.5 ─ LH west wall
X=+29 ──  LH/SC center, Promotion belt X
X=+37.5 ─ LH/SC east wall
X=+44 ──  Lobby + Search Counter plaza
X=+52 ──  Big Consolidation Table
X=+54 ──  Big Table east edge (3 straight belt start)
X=+62 ──  Truck rear (3 trucks)
X=+66~+68 Truck cabs (facing east)
```

---

## 8. 원본 설계 vs v10 — 변경 요약

| 항목 | 원본 설계 | v10 구현 | 사유 |
| --- | --- | --- | --- |
| Zone 0 Lobby | 독립 + 게이트 + JWT 라이트 | Zone 7과 통합, 게이트 제거 | 단순화 / 사용자 요청 |
| Zone 3.5 Audit Gate | 별도 검사대 | **제거됨** | 단순화 / 사용자 요청 |
| Zone 4 Lakehouse 내부 | 통로식 선반 + LED | Storage table 그리드 (5×4) | 사용자 요청 |
| Zone 5 Showcase | 받침대 + 스포트라이트 | 거실 진열장 (글래스 캐비닛) | 사용자 요청 |
| Zone 6 Catalog Office | 유리벽 사무실 + 모니터 | **제거됨** | 단순화 / 사용자 요청 |
| Dock 테이블 | 3개 (각 dock별) | 1개 Big Consolidation Table | 사용자 요청 |
| Dock 출고 belt | LH/SC → 각 dock 분기 (6 belts + bends) | Big Table → 3 직선 belt | 자연스러운 흐름 |
| 트럭 방향 | (불명) | cab 동쪽, rear 서쪽 (open rear toward table) | 사용자 요청 |
| 트럭 바퀴 | (불명) | 4 wheels (1 trailer + 1 cab axle) | 사용자 요청 |
| 박스 워크로드별 변형 | 두루마리/폴더/테이블 | **미구현** | 후속 작업 |
| 사용자 아바타 시스템 | 실시간 + Keycloak 연동 | 정적 마네킹 5개 | Phase 6+ |
| Lineage 광선 네트워크 | 풀-fledged | 데모 3 줄만 | Phase 6+ |
| 박스 부유 이동 (call) | 자동 부유 이동 | replay 이벤트 단계 위치만 변경 | Phase 6+ |

---

## 9. 후속 작업 (Phase 6+ 후보)

- [ ] file_registry 바이패스 시각화 (Probing → Redis 직행 라인)
- [ ] Delta Mode 박스 변형 (작은 큐브)
- [ ] Integrity Audit 시각 알람 (재추가 검토)
- [ ] Catalog Office 재추가 (Portal monitor 미러)
- [ ] Keycloak 실시간 아바타 (게이트 통과, 권한 거부)
- [ ] 박스 부유 이동 애니메이션 (search → counter → dock)
- [ ] 워크로드별 박스 변형 (AI 두루마리, HPC 폴더, HPDA 가상 테이블)
- [ ] Lakehouse 풀 lineage 광선 네트워크
- [ ] Portal WebRTC 동기화 (Twin Control Tower 안 모니터)
