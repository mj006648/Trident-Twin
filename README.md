# Trident Omniverse Twin PoC

Omniverse/Isaac Sim에서 **Trident Lakehouse의 Accumulation → Metadata → Staging/Serving 흐름**을 디지털 트윈으로 표현하기 위한 최소 PoC입니다.

이 PoC의 목표는 단순 3D 시각화가 아니라, `Dataset`, `Metadata`, `Lake`, `Lakehouse`, `Workload Interface`를 USD Prim과 상태 이벤트로 연결하는 것입니다.

## 1. 개념

사용자가 작성한 abstraction 구성도를 아래와 같이 Omniverse runtime으로 매핑합니다.

| Abstraction | Twin Entity | USD 표현 |
|---|---|---|
| Lake | `lake.bronze` | 왼쪽 대형 저장소 영역 |
| Accumulation | `pipeline.accumulation` | 컨베이어 라인 |
| Explaining Metadata | `station.metadata.explaining` | 파란 메타데이터 스테이션 |
| Sharing Metadata | `station.metadata.sharing` | 초록 메타데이터 스테이션 |
| Lakehouse | `lakehouse.silver` | 오른쪽 저장소/랙 영역 |
| Staging | `pipeline.staging` | Lakehouse 상단/우측 진열 라인 |
| Adaptive Workload Interfaces | `workload.*` | HPC/M&S/AI/HPDA 요청자 |
| Operator Desk | `operator.control` | 중앙 관제 콘솔 |
| Dataset Package | `dataset.sample.001` | 움직이는 데이터 패키지 |

## 2. 생성되는 결과물

```text
stages/trident_lakehouse_twin.usda       # 기본 USD stage
stages/trident_lakehouse_twin_replay.usda # 이벤트 애니메이션이 들어간 stage
```

## 3. 실행

Isaac Sim Python으로 실행해야 합니다. 일반 Python에서는 `pxr` 모듈이 안 잡힐 수 있습니다.

```bash
cd /home/chang/git/trident-omniverse-twin-poc
/home/chang/isaac-sim/python.sh scripts/create_scene.py
/home/chang/isaac-sim/python.sh scripts/replay_events.py
```

생성된 파일을 Isaac Sim에서 엽니다.

```text
/home/chang/git/trident-omniverse-twin-poc/stages/trident_lakehouse_twin_replay.usda
```

GUI에서 열 때는 Isaac Sim 실행 후 `File → Open`으로 위 stage를 열면 됩니다.

## 4. 현재 PoC 동작

`dataset.sample.001`이 다음 상태 전이를 따라 이동합니다.

```text
raw_arrived
→ stored_in_lake
→ explaining_metadata_generated
→ sharing_metadata_published
→ staged_in_lakehouse
→ requested_by_ai_workload
→ served_to_workload
```

상태 전이에 따라 USD Prim의 위치와 custom attribute가 갱신됩니다.

## 5. 중요한 설계 원칙

이 PoC에서 데이터 파일이 실제로 이동하는 것이 아닙니다. Omniverse는 **데이터셋 상태 전이의 공간적 표현**을 담당합니다.

```text
실제 상태 source of truth:
  Redis / Milvus / PostgreSQL / Iceberg / Nessie / Stats Service

Omniverse 역할:
  USD Prim, scene hierarchy, 상태 시각화, 이벤트 replay, 운영자 상호작용
```

## 6. 다음 단계

1. Portal `TridentTwin.tsx`에서 이 stage를 WebRTC viewer로 확인
2. `data/mock_twin_events.json` 대신 Stats Service `/api/twin/events` 연결
3. Prim click 또는 Portal selection으로 `entity_id` 연동
4. Redis/Milvus/Iceberg 실제 상태를 `trident:*` USD attribute로 투영
5. AI/HPC/HPDA 워크로드 요청 시나리오 추가

## 7. 논문/제안서 표현

> 본 디지털 트윈은 데이터 저장소의 단순 3D 시각화가 아니라, Lake–Metadata–Lakehouse–Workflow 사이에서 발생하는 데이터셋 상태 전이와 워크로드 요청 과정을 USD 기반 공간 모델로 표현하는 운용형 트윈이다.
