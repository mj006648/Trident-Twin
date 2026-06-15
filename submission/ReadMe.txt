2026 C&S Project 최종 제출 파일
Team-Code / Trident Lakehouse Digital Twin

1. 프로젝트 개요
본 프로젝트는 Trident Lakehouse의 데이터 흐름을 NVIDIA Isaac Sim / Omniverse 기반 3D Digital Twin으로 시각화하는 프로젝트입니다.
Raw Bucket, Accumulation, Lakehouse, Search, Data Staging, Delivery Zone을 통해 데이터 적재, 메타데이터 생성, Iceberg 테이블화, 자연어 검색, Gemma4 기반 분석, AI Workload 전달 흐름을 확인할 수 있습니다.

2. 제출 패키지 구성
- ReadMe.txt
  - 본 파일입니다. 실행 방법, 버전 정보, 포함 파일을 설명합니다.
- Trident-Twin/exts/trident.twin/
  - Isaac Sim / Omniverse Extension 소스입니다.
  - Extension 이름: trident.twin
  - Extension 버전: 0.1.0
- Trident-Twin/stages/
  - USD/USDA Scene 파일입니다.
  - 최신 제출용 Scene: trident_lakehouse_twin_20260615_1338.usda
  - 기본 Scene: trident_lakehouse_twin.usda
- Trident-Twin/twin-hub/
  - Portal/Lakehouse 상태를 Isaac Sim Extension에 전달하는 FastAPI 기반 bridge 서버입니다.
  - 외부 컴퓨터에서는 fixture mode로 실행할 수 있습니다.
- Trident-Twin/data/
  - 외부 실행용 mock/fixture entity 데이터입니다.
- Trident-Twin/scripts/
  - Scene 생성, 카메라 추가, screenshot/diagram 생성, live sync 보조 스크립트입니다.
- Trident-Twin/docs/
  - 설계 문서, zone diagram, 실제 scene screenshot입니다.
- integration/
  - 실제 Trident Portal 및 Kubernetes/ArgoCD 연동 참고 파일입니다.
  - 외부 컴퓨터 단독 실행에는 필수는 아니며, 실제 클러스터 배포/연동을 재현할 때 참고합니다.

3. 개발 및 실행에 사용한 버전
- Omniverse / Isaac Sim 앱 버전: NVIDIA Isaac Sim 5.1.0
- 사용 Docker image: nvcr.io/nvidia/isaac-sim:5.1.0
- Isaac Sim Extension: trident.twin 0.1.0
- Extension dependency: omni.usd, omni.ui
- Python: 3.12 계열 권장
- twin-hub dependency: fastapi, uvicorn
- 실제 클러스터 배포 이미지 참고
  - trident-twin-hub: ich6648/trident-twin-hub:v0.1.8
  - trident-portal: ich6648/trident-portal:v97.147
  - trident-stats: ich6648/trident-stats:v6.39

4. 외부 컴퓨터에서 최소 실행 방법
아래 방법은 실제 Trident Kubernetes 클러스터 없이도 Digital Twin Scene과 Extension을 확인하기 위한 fixture mode 실행 방법입니다.

4.1 twin-hub 실행
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

4.2 Isaac Sim / Omniverse에서 Extension 등록
1) NVIDIA Isaac Sim 5.1.0을 실행합니다.
2) Extension 검색 경로에 다음 폴더를 추가합니다.

  Trident-Twin/exts

3) Extension Manager에서 trident.twin을 Enable 합니다.
4) 다음 Scene 파일을 엽니다.

  Trident-Twin/stages/trident_lakehouse_twin_20260615_1338.usda

5) live bridge를 사용하려면 Isaac Sim 실행 환경에 다음 환경변수를 설정합니다.

  TWIN_HUB_URL=http://127.0.0.1:8765

4.3 Docker Isaac Sim headless 실행 예시
환경마다 GPU, IP, 포트가 다르므로 아래는 참고 예시입니다.

  cd /isaac-sim
  TWIN_HUB_URL=http://<twin-hub-host>:8765   ./runheadless.sh     --/app/livestream/publicEndpointAddress=<public-ip>     --ext-folder /path/to/Trident-Twin/exts     --enable trident.twin

본 프로젝트 개발 환경에서는 Isaac Sim 5.1.0 Docker container에서 실행했습니다.

5. 실제 클러스터 live mode 참고
실제 Trident 환경에서는 Portal Digital Twin 화면이 Isaac Sim WebRTC stream을 보여주고, Portal의 Data Search / Data Staging / Gemma4 질문 이벤트가 twin-hub를 통해 Isaac Extension으로 전달됩니다.
외부 컴퓨터에서 이 기능까지 재현하려면 integration 폴더의 Portal API 파일과 ArgoCD manifest를 참고하여 다음 컴포넌트가 필요합니다.

- Trident Portal
- trident-stats service
- trident-twin-hub
- Milvus / Redis / PostgreSQL / Iceberg / Nessie / Ceph S3
- Gemma4 serving endpoint
- Keycloak 인증 설정

6. 주요 기능
- Zone Camera: Raw Bucket, Accumulation, Lakehouse, Staging, Search, Delivery Zone camera preset 이동
- Raw Bucket Zone: raw dataset 단위 slot/box 시각화
- Accumulation Zone: Step 1 / Step 2 / Step 3 진행 상태를 box 이동으로 표시
- Lakehouse Zone: dataset별 Iceberg table을 data/metadata 역할에 따라 시각화
- Search Zone: 로그인 사용자 role 및 데이터 검색 흐름 표현
- Data Staging Zone: 이전에 선택한 데이터 bundle을 staging table 위에 보관/재사용
- Delivery Zone: 선택된 데이터 copy가 Big Table을 거쳐 AI Workload 방향으로 이동
- Gemma4 Q&A 연동: 선택 데이터의 bounded Lakehouse context를 사용해 질의응답 수행

7. 주의 사항
- Omniverse/Isaac Sim은 데이터 원본 저장소가 아니라 Digital Twin viewer 및 event bridge입니다.
- 실제 데이터 원본은 Ceph S3, Iceberg/Nessie, PostgreSQL, Milvus, Redis 등 Lakehouse backend에 있습니다.
- 외부 컴퓨터 단독 실행에서는 fixture mode로 Scene과 Extension 동작을 확인합니다.
- 실제 live mode는 내부 IP, Kubernetes namespace, Keycloak credential, Gemma4 endpoint가 필요합니다.

8. 제출 기준 포함 여부
- USD/USDA 파일 포함: 예
- Isaac Sim Extension 포함: 예
- 추가 실행 모듈(twin-hub, scripts, data) 포함: 예
- 개발 Omniverse 앱 버전 기재: 예, NVIDIA Isaac Sim 5.1.0
- Extension 버전 기재: 예, trident.twin 0.1.0
