2026 C&S Project 최종 제출 파일
Team-Code / Trident Lakehouse Digital Twin

1. 프로젝트 개요
본 프로젝트는 Trident Lakehouse의 데이터 흐름을 NVIDIA Isaac Sim / Omniverse 기반 3D Digital Twin으로 시각화하는 프로젝트입니다.
Raw Bucket, Accumulation, Lakehouse, Search, Data Staging, Delivery Zone을 통해 데이터 적재, 메타데이터 생성, Iceberg 테이블화, 자연어 검색, Gemma4 기반 분석, AI Workload 전달 흐름을 확인할 수 있습니다.

본 제출 패키지는 두 가지 검증 경로를 제공합니다.

- A안: 실제 연동 데모 재현
  - AI대학원/SmartX 내부망에서 Trident Portal에 접속하여 발표 데모와 같은 흐름을 재현합니다.
  - 실제 Kubernetes, ArgoCD, Keycloak, Lakehouse backend, Gemma4 endpoint, Isaac Sim WebRTC stream이 이미 연결된 운영 환경을 사용합니다.
- B안: 외부 컴퓨터 fixture mode 재현
  - 실제 클러스터 없이 제출 패키지 안의 USD/USDA scene, Isaac Sim extension, twin-hub fixture 데이터를 사용해 scene과 command bridge 동작을 확인합니다.

실제 Trident live mode는 여러 오픈소스/인프라 컴포넌트가 필요합니다. 외부 PC에 모든 컴포넌트를 새로 설치하는 방식보다, 검증자는 동일한 Omniverse/Isaac Sim 앱 버전 기준에서 A안의 Portal 데모 절차를 따라 실제 연동 결과를 확인하는 것이 가장 정확합니다.

2. 제출 패키지 구성
- ReadMe.txt
  - 본 파일입니다. 실행 방법, 버전 정보, 포함 파일, 실제 데모 재현 절차를 설명합니다.
- Trident-Twin/README.md
  - Trident-Twin 저장소의 상세 설명 문서입니다.
- Trident-Twin/exts/trident.twin/
  - Isaac Sim / Omniverse Extension 소스입니다.
  - Extension 이름: trident.twin
  - Extension 버전: 0.1.0
- Trident-Twin/stages/
  - USD/USDA Scene 파일입니다.
  - 제출용 Scene: trident_lakehouse_twin_20260615_1338.usda
  - 기본 Scene: trident_lakehouse_twin.usda
  - Replay Scene: trident_lakehouse_twin_replay.usda
- Trident-Twin/twin-hub/
  - Portal/Lakehouse 상태를 Isaac Sim Extension에 전달하는 FastAPI 기반 bridge 서버입니다.
  - 외부 컴퓨터에서는 fixture mode로 실행할 수 있습니다.
- Trident-Twin/data/
  - 외부 실행용 mock/fixture entity 및 event 데이터입니다.
- Trident-Twin/scripts/
  - Scene 생성, 카메라 추가, screenshot/diagram 생성, live sync 보조 스크립트입니다.
- Trident-Twin/docs/
  - 설계 문서, zone diagram, 실제 scene screenshot입니다.
- integration/
  - 실제 Trident Portal 및 Kubernetes/ArgoCD 연동 참고 파일입니다.
  - 외부 컴퓨터 단독 실행에는 필수는 아니며, 실제 클러스터 배포/연동 구조를 확인할 때 참고합니다.

3. 개발 및 실행에 사용한 버전
- Omniverse / Isaac Sim 앱 버전: NVIDIA Isaac Sim 5.1.0
- 사용 Docker image: nvcr.io/nvidia/isaac-sim:5.1.0
- Isaac Sim Extension: trident.twin 0.1.0
- Extension dependency: omni.usd, omni.ui
- Python: 3.12 계열 권장
- twin-hub dependency: fastapi, uvicorn
- 실제 클러스터 배포 이미지 참고
  - trident-twin-hub: ich6648/trident-twin-hub:v0.1.10
  - trident-portal: ich6648/trident-portal:v97.153
  - trident-stats: ich6648/trident-stats:v6.42

4. A안: 실제 연동 데모 재현 방법
이 방법은 발표 데모와 가장 동일한 검증 경로입니다. AI대학원/SmartX 내부망에서 접속 가능한 환경을 기준으로 합니다.

4.1 접속 조건
- AI대학원/SmartX 내부망 또는 해당 내부망에 접근 가능한 네트워크가 필요합니다.
- 브라우저에서 다음 Portal에 접속합니다.

  http://10.38.38.217

- Portal 로그인 권한이 필요할 수 있습니다.
- Isaac Sim WebRTC stream은 내부 Isaac Sim host와 signaling port를 사용합니다.
  - Isaac Sim host: 10.38.38.197
  - Signaling port: 49100

4.2 데모 재현 순서
1) 브라우저에서 http://10.38.38.217 에 접속합니다.
2) Portal 메뉴에서 Digital Twin을 클릭합니다.
3) 왼쪽 영역에 Isaac Sim / Omniverse WebRTC stream이 표시되는지 확인합니다.
4) 오른쪽 Digital Twin Control 패널에서 Zone Camera 탭을 엽니다.
5) 다음 camera preset을 차례대로 클릭하여 scene zone 이동을 확인합니다.
   - Overview Full
   - Raw Bucket Zone
   - Accumulation Zone
   - Lakehouse Zone
   - Staging Zone
   - Search Zone
   - Delivery Zone
   - Control Tower Zone
6) Data Search 탭을 엽니다.
7) All Datasets 또는 Single Dataset을 선택합니다.
8) 예시 query를 입력하고 Search를 클릭합니다.

   sepsis cohort lactate antibiotics

9) 검색 결과 candidate를 1개 이상 선택합니다.
10) 선택한 Lakehouse table이 Isaac scene의 Lakehouse Zone에서 highlight 되는지 확인합니다.
11) 질문 입력창에 예시 질문을 입력합니다.

   선택한 실제 데이터 샘플과 통계를 기반으로 패혈증 위험 패턴을 쉽게 설명해줘.

12) Ask Gemma4 with Selection 버튼을 클릭합니다.
13) 다음 visual flow를 확인합니다.
   - 선택 bundle이 Data Staging에 저장됩니다.
   - 선택 데이터 copy가 Big Table 방향으로 이동합니다.
   - 이후 AI Bus 방향으로 workload delivery animation이 이어집니다.
   - Gemma4 응답이 Portal UI에 표시됩니다.
14) Data Staging 탭을 열어 이전에 질문한 데이터 bundle이 Dataset Basket처럼 남아 있는지 확인합니다.
15) 저장된 bundle을 다시 클릭하면 해당 bundle이 재선택되고 scene에서 다시 highlight/delivery 흐름을 확인할 수 있습니다.
16) Stop Workload 버튼을 누르면 highlight/delivery visual state가 정리됩니다.

4.3 실제 연동 구성
실제 Portal live mode는 다음 구성요소가 이미 배포된 환경에서 동작합니다.

- Trident Portal
- trident-stats service
- trident-twin-hub
- NVIDIA Isaac Sim / Omniverse WebRTC stream
- Ceph S3 raw bucket
- Apache Iceberg / Nessie catalog
- Milvus semantic search
- Redis cache/evidence store
- PostgreSQL catalog/governance store
- Keycloak authentication
- Gemma4 serving endpoint
- Kubernetes / ArgoCD deployment

따라서 외부 컴퓨터에서 위 전체 live mode를 새로 재현하려면 integration 폴더의 Portal API 파일과 ArgoCD manifest를 참고해야 합니다. 단, 전체 인프라 설치는 제출 패키지의 최소 검증 경로가 아니라 실제 운영 환경 재배포에 해당합니다.

5. B안: 외부 컴퓨터에서 fixture mode 최소 실행 방법
아래 방법은 실제 Trident Kubernetes 클러스터 없이도 Digital Twin Scene과 Extension을 확인하기 위한 fixture mode 실행 방법입니다.

5.1 twin-hub 실행
터미널에서 다음을 실행합니다.

  cd Trident-Twin
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements-twin-hub.txt
  cd twin-hub
  uvicorn app:app --host 0.0.0.0 --port 8765

정상 실행 확인:

  http://127.0.0.1:8765/api/twin/health
  http://127.0.0.1:8765/api/twin/entities

TRIDENT_STATS_BASE_URL 환경변수를 설정하지 않으면 twin-hub는 Trident-Twin/data 아래 fixture 데이터를 사용합니다.

5.2 Isaac Sim / Omniverse에서 Extension 등록
1) NVIDIA Isaac Sim 5.1.0을 실행합니다.
2) Extension 검색 경로에 다음 폴더를 추가합니다.

  Trident-Twin/exts

3) Extension Manager에서 trident.twin을 Enable 합니다.
4) 다음 Scene 파일을 엽니다.

  Trident-Twin/stages/trident_lakehouse_twin_20260615_1338.usda

5) live bridge를 사용하려면 Isaac Sim 실행 환경에 다음 환경변수를 설정합니다.

  TWIN_HUB_URL=http://127.0.0.1:8765

6) Extension의 Trident Twin Live 창에서 Start Live를 누르거나, 자동 polling 상태를 확인합니다.
7) fixture mode에서는 실제 Portal/Gemma4/Lakehouse 없이 mock entity와 command bridge 구조를 확인합니다.

5.3 Docker Isaac Sim headless 실행 예시
환경마다 GPU, IP, 포트가 다르므로 아래는 참고 예시입니다.

  cd /isaac-sim
  TWIN_HUB_URL=http://<twin-hub-host>:8765 ./runheadless.sh \
    --/app/livestream/publicEndpointAddress=<public-ip> \
    --ext-folder /path/to/Trident-Twin/exts \
    --enable trident.twin

본 프로젝트 개발 환경에서는 Isaac Sim 5.1.0 Docker container에서 실행했습니다.

6. 주요 기능
- Zone Camera: Raw Bucket, Accumulation, Lakehouse, Staging, Search, Delivery Zone camera preset 이동
- Raw Bucket Zone: raw dataset 단위 slot/box 시각화
- Accumulation Zone: Step 1 / Step 2 / Step 3 진행 상태를 box 이동으로 표시
- Lakehouse Zone: dataset별 Iceberg table을 data/metadata 역할에 따라 시각화
- Search Zone: 로그인 사용자 role 및 데이터 검색 흐름 표현
- Data Staging Zone: 이전에 선택한 데이터 bundle을 staging table 위에 보관/재사용
- Delivery Zone: 선택된 데이터 copy가 Big Table을 거쳐 AI Workload 방향으로 이동
- Gemma4 Q&A 연동: 선택 데이터의 bounded Lakehouse context를 사용해 질의응답 수행
- twin-hub command bridge: Portal event를 camera/highlight/staging/delivery/workload command로 변환

7. 주의 사항
- Omniverse/Isaac Sim은 데이터 원본 저장소가 아니라 Digital Twin viewer 및 event bridge입니다.
- 실제 데이터 원본은 Ceph S3, Iceberg/Nessie, PostgreSQL, Milvus, Redis 등 Lakehouse backend에 있습니다.
- 외부 컴퓨터 단독 실행에서는 fixture mode로 Scene과 Extension 동작을 확인합니다.
- 실제 live mode는 내부 IP, Kubernetes namespace, Keycloak credential, Gemma4 endpoint가 필요합니다.
- 실제 클러스터 배포 source of truth는 SmartX-Team/TwinX-Ops ArgoCD repository이며, 배포 변경은 PR/merge 절차로 수행합니다.

8. 제출 기준 포함 여부
- USD/USDA 파일 포함: 예
- Isaac Sim Extension 포함: 예
- 추가 실행 모듈(twin-hub, scripts, data) 포함: 예
- 실제 연동 데모 재현 절차 포함: 예, AI대학원/SmartX 내부망 Portal 접속 절차 기재
- 개발 Omniverse 앱 버전 기재: 예, NVIDIA Isaac Sim 5.1.0
- Extension 버전 기재: 예, trident.twin 0.1.0
