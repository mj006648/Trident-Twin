import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import matplotlib.patheffects as pe

W, H = 38, 24
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')
fig.patch.set_facecolor('#0c1520')

# ── 팔레트 ──────────────────────────────────────────────────
BG    = '#0c1520'
CYAN  = '#00d4ff'
YEL   = '#ffd93d'
GRN   = '#4ecb71'
RED   = '#e05252'
PUR   = '#b07fff'
ORG   = '#ff9f43'
BLUE  = '#4a90d9'
NVIDG = '#76b900'
PG    = '#5b9bd5'
DIMW  = '#8aaabb'
DIMB  = '#1a3050'

def box(x, y, w, h, fc, ec='none', lw=0, alpha=1.0, r=0.3, zorder=3):
    p = FancyBboxPatch((x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={r}",
        facecolor=fc, edgecolor=ec, linewidth=lw, alpha=alpha, zorder=zorder)
    ax.add_patch(p)

def t(x, y, s, sz=8, c='white', ha='center', va='center', bold=False, z=6, wrap=False):
    ax.text(x, y, s, fontsize=sz, color=c, ha=ha, va=va,
            fontweight='bold' if bold else 'normal', zorder=z,
            linespacing=1.35)

def a(x1, y1, x2, y2, c, lw=2, rad=0.0, lbl='', lo=(0,0), z=7):
    ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle='->', color=c, lw=lw,
                        connectionstyle=f'arc3,rad={rad}'),
        zorder=z)
    if lbl:
        mx = (x1+x2)/2 + lo[0]
        my = (y1+y2)/2 + lo[1]
        ax.text(mx, my, lbl, fontsize=6.0, color=c, ha='center', va='center',
                zorder=z+1, fontweight='bold',
                bbox=dict(boxstyle='round,pad=0.18', fc=BG, ec='none', alpha=0.9))

# ═══════════════════════════════════════════════════════════════════════
# 제목
# ═══════════════════════════════════════════════════════════════════════
box(0.2, 22.5, 37.6, 1.3, '#0a1628', ec=CYAN, lw=1.5, r=0.4)
t(19, 23.28, '1B. X+AI Services Project Overview', 18, CYAN, bold=True)
t(19, 22.82, 'Trident Data Lakehouse Pipeline Twin & AI Predictive Simulator  |  Cloud-Native on Kubernetes  |  GitOps via ArgoCD', 9, DIMW)

# ═══════════════════════════════════════════════════════════════════════
# 영역 배경 3개
# ═══════════════════════════════════════════════════════════════════════
# END (좌측)
box(0.2, 0.2, 5.8, 22.1, '#0a1e32', ec='#1a4060', lw=1.2, alpha=0.55, r=0.5)
t(3.1, 22.1, 'END', 13, CYAN, bold=True)

# EDGE (중앙)
box(6.2, 0.2, 19.6, 22.1, '#081e28', ec='#1a4a5a', lw=1.2, alpha=0.55, r=0.5)
t(16.0, 22.1, 'EDGE  —  Lakehouse Pipeline (Cloud-Native Pods on Kubernetes)', 13, CYAN, bold=True)

# CORE (우측)
box(26.0, 0.2, 11.8, 22.1, '#08101e', ec='#1a3050', lw=1.2, alpha=0.55, r=0.5)
t(31.9, 22.1, 'CORE', 13, CYAN, bold=True)

# ═══════════════════════════════════════════════════════════════════════
# END: Web Portal
# ═══════════════════════════════════════════════════════════════════════
box(0.4, 14.0, 5.4, 8.0, DIMB, ec=CYAN, lw=1.5, r=0.35)
t(3.1, 21.7, 'Web Portal', 12, CYAN, bold=True)
t(3.1, 21.3, 'Next.js + Tailwind CSS', 8, DIMW)

# Pipeline Control
box(0.55, 19.5, 5.1, 2.2, '#0a1a2e', ec=BLUE, lw=1.0, r=0.2)
t(3.1, 21.4, 'Pipeline Control', 8.5, BLUE, bold=True)
t(3.1, 21.05, 'Trigger Lakehouse pipeline execution', 6.5, DIMW)
t(3.1, 20.75, 'Monitor running Spark jobs', 6.5, DIMW)
t(3.1, 20.45, 'Approve AI schema design proposals', 6.5, DIMW)
t(3.1, 20.0, 'OUT  REST POST /api/pipeline/trigger', 6.5, BLUE, bold=True)
t(3.1, 19.72, '(dataset path, schema, mode)', 6, DIMW)

# Pipeline Simulation
box(0.55, 17.0, 5.1, 2.2, '#140a24', ec=PUR, lw=1.0, r=0.2)
t(3.1, 18.9, 'Pipeline Simulation', 8.5, PUR, bold=True)
t(3.1, 18.55, 'Input dataset profile before actual run', 6.5, DIMW)
t(3.1, 18.25, '(file count, size, schema complexity...)', 6.5, DIMW)
t(3.1, 17.95, 'View XGBoost prediction:', 6.5, DIMW)
t(3.1, 17.65, '  bottleneck zone / stage duration / resource', 6.2, DIMW)
t(3.1, 17.25, 'OUT  REST POST /api/simulate', 6.5, PUR, bold=True)
t(3.1, 16.97, '(input profile)', 6, DIMW)

# 3D Twin View
box(0.55, 14.15, 5.1, 2.6, '#081508', ec=NVIDG, lw=1.0, r=0.2)
t(3.1, 16.45, '3D Pipeline Twin View', 8.5, NVIDG, bold=True)
t(3.1, 16.1, 'Embedded in browser  -  no client install', 6.5, DIMW)
t(3.1, 15.8, 'Interactive 3D scene from Omniverse', 6.5, DIMW)
t(3.1, 15.45, 'IN  WebRTC (UDP/Video)', 6.5, NVIDG, bold=True)
t(3.1, 15.17, 'Omniverse Server -> Portal stream', 6, DIMW)

# END: ArgoCD
box(0.4, 0.4, 5.4, 13.3, DIMB, ec=RED, lw=1.5, r=0.35)
t(3.1, 13.4, 'ArgoCD', 12, RED, bold=True)
t(3.1, 13.0, 'GitOps Controller', 8, '#d88080')
t(3.1, 12.55, 'Polls Git repo (Twinx) for manifest changes', 7, DIMW)
t(3.1, 12.2, 'Deploys ALL pipeline pods to K8s:', 7, DIMW)
t(3.1, 11.85, '  Spark Operator, Nessie, Milvus, Redis', 6.5, DIMW)
t(3.1, 11.55, '  Trino, Ollama, FastAPI, PostgreSQL', 6.5, DIMW)
t(3.1, 11.25, '  Omniverse Kit Extension', 6.5, DIMW)
t(3.1, 10.9, 'Monitors pod health, auto-restarts on failure', 7, DIMW)
t(3.1, 10.5, 'OUT  kubectl apply (K8s manifests)', 7, RED, bold=True)
t(3.1, 10.2, '-> deploys all EDGE + CORE pods', 6.5, DIMW)

# Git repo box
box(0.55, 0.55, 5.1, 2.2, '#0a1218', ec='#445', lw=1, r=0.2)
t(3.1, 2.45, 'Git Repo: Twinx', 8, '#aaa', bold=True)
t(3.1, 2.15, 'K8s manifests / Helm charts / ArgoCD apps', 6.5, '#666')
t(3.1, 1.85, 'Single source of truth for infra state', 6.5, '#666')
t(3.1, 1.3, 'ArgoCD polls this repo continuously', 6.5, '#555', bold=True)

# ═══════════════════════════════════════════════════════════════════════
# EDGE  (수직 흐름: Phase1 위 -> Phase2 중 -> Phase3 아래)
# ═══════════════════════════════════════════════════════════════════════

# ── Phase 1: Ingest ──────────────────────────────────────────────────
box(6.4, 15.0, 19.2, 6.8, '#140a08', ec=RED, lw=2.0, r=0.35)
t(16.0, 21.5, 'Phase 1  |  Ingest', 11, RED, bold=True)
t(16.0, 21.1, 'Spark Operator (Kubernetes-native Spark)  +  Ollama LLM (qwen2.5-coder)', 7.5, '#d88080')

# Phase1 sub-boxes: 3 columns
# [Multi-Format Probing] [AI Schema Design] [Iceberg Creation + URI Detection]
box(6.6, 17.4, 4.3, 3.3, '#1e0a08', ec='#803030', lw=0.9, r=0.2)
t(8.75, 20.45, 'Multi-Format Probing', 7.5, RED, bold=True)
t(8.75, 20.1, 'Scan user METADATA path in S3', 6.5, DIMW)
t(8.75, 19.8, 'Auto-detect: JSON / CSV / TSV', 6.5, DIMW)
t(8.75, 19.5, 'Each file -> candidate Iceberg table', 6.5, DIMW)
t(8.75, 19.2, 'With metadata: AI proposes schema', 6.5, DIMW)
t(8.75, 18.9, 'No metadata: AI dialog mode', 6.5, DIMW)
t(8.75, 18.3, 'IN: S3 bucket path', 6, RED, bold=True)
t(8.75, 18.0, 'Cardinality-based partition validation', 6, DIMW)

box(11.1, 17.4, 4.7, 3.3, '#1e0a08', ec='#803030', lw=0.9, r=0.2)
t(13.45, 20.45, 'AI Schema Design', 7.5, RED, bold=True)
t(13.45, 20.1, 'Ollama qwen2.5-coder', 6.5, DIMW)
t(13.45, 19.8, 'Propose: partition key, column desc', 6.5, DIMW)
t(13.45, 19.5, 'Cardinality analysis -> validate partition', 6.5, DIMW)
t(13.45, 19.2, 'User reviews & approves in Portal', 6.5, DIMW)
t(13.45, 18.9, 'No metadata mode: full AI dialog', 6.5, DIMW)
t(13.45, 18.3, 'OUT: approved table+column+partition schema', 6, RED, bold=True)

box(16.0, 17.4, 9.4, 3.3, '#1e0a08', ec='#803030', lw=0.9, r=0.2)
t(20.7, 20.45, 'Iceberg Table Creation  +  URI Detection  +  trident_search_index', 7.5, RED, bold=True)
t(20.7, 20.1, 'Spark creates Iceberg tables via Nessie catalog (approved schema)', 6.5, DIMW)
t(20.7, 19.8, 'URI Detection (2-step): col-name scan (filename/file_path)  ->  extension pattern (.jpg/.bin/.dcm)', 6.5, DIMW)
t(20.7, 19.5, 'No URI found -> file_registry: recursive S3 scan, auto-create Iceberg registry table', 6.5, DIMW)
t(20.7, 19.2, 'AI joins multi-tables (Fact + optimal Join key/type) -> trident_search_index unified view', 6.5, DIMW)
t(20.7, 18.9, 'Zero-Copy: raw files NEVER moved, only S3 URI pointers stored in Iceberg rows', 6.5, GRN)
t(20.7, 18.3, 'OUT: Iceberg tables committed to Nessie  |  trident_search_index ready', 6, RED, bold=True)

# Integrity Audit (Phase1 완료 후)
box(6.6, 15.15, 19.0, 2.0, '#14100a', ec='#804020', lw=0.8, r=0.2)
t(16.1, 16.9, 'Integrity Audit  (after each ingest)', 7.5, ORG, bold=True)
t(16.1, 16.55, 'Compare: S3 source file count  vs  Iceberg index row count  ->  compute integrity_pct', 6.5, DIMW)
t(16.1, 16.25, 'search_index mode (metadata-driven)  vs  file_registry mode (S3-scan-driven)', 6.5, DIMW)
t(16.1, 15.9, 'Audit result cached to Redis  [trident:audit:{namespace}]  |  displayed in Portal Integrity Audit page', 6.5, DIMW)
t(16.1, 15.35, 'OUT: integrity_pct  +  audit record -> Redis cache', 6, ORG, bold=True)

# ── Ceph S3 (EDGE 우측, Phase1 옆) ──────────────────────────────────
# 이미 EDGE 내에 있지만 Ceph는 독립 컴포넌트
# Nessie와 Ceph는 Phase1 오른쪽 아래에 배치 (공유 인프라)

# ── Phase 2: Metadata ────────────────────────────────────────────────
box(6.4, 9.5, 19.2, 5.2, '#0d0a1e', ec=PUR, lw=2.0, r=0.35)
t(16.0, 14.4, 'Phase 2  |  Metadata Indexing', 11, PUR, bold=True)
t(16.0, 14.0, 'Milvus  (Semantic Vector Index)   +   Redis  (Partition Cache / Storage Index)', 7.5, '#c39bd3')

box(6.6, 9.65, 9.0, 4.5, '#0d0820', ec='#7040c0', lw=0.9, r=0.2)
t(11.1, 13.85, 'Milvus  —  Semantic Search Index', 8, PUR, bold=True)
t(11.1, 13.5, '3-Layer Super Context  (per dataset, NOT per row):', 6.5, DIMW)
t(11.1, 13.2, '  Layer 1: User-provided description', 6.2, DIMW)
t(11.1, 12.95, '  Layer 2: AI-generated summary (schema + sample values via Ollama)', 6.2, DIMW)
t(11.1, 12.7, '  Layer 3: Column names + statistics + data types', 6.2, DIMW)
t(11.1, 12.4, 'Embed Super Context via Ollama bge-m3 -> 1 vector per dataset', 6.5, PUR)
t(11.1, 12.1, 'Index size proportional to # datasets, NOT data volume', 6.5, DIMW)
t(11.1, 11.8, 'Cosine similarity search -> top-5 table candidates', 6.5, DIMW)
t(11.1, 11.5, 'Fields: table_full_name / table_type / rich_context / vector', 6.5, DIMW)
t(11.1, 10.9, 'IN: trident_search_index schema + Ollama embedding', 6.5, PUR, bold=True)
t(11.1, 10.6, 'OUT: top-5 candidates (name, type, rich_context, distance)', 6.5, PUR, bold=True)
t(11.1, 9.8, 'Phase 3 Search: Milvus query -> user selects table', 6, '#7a60b0')

box(15.8, 9.65, 9.6, 4.5, '#200808', ec='#c04040', lw=0.9, r=0.2)
t(20.6, 13.85, 'Redis  —  Storage Search Index  (Partition Cache)', 8, RED, bold=True)
t(20.6, 13.5, 'Cache Iceberg Manifest files as Redis ReJSON structure', 6.5, DIMW)
t(20.6, 13.2, 'Partition-level granularity:', 6.5, DIMW)
t(20.6, 12.95, '  partition key + value range + S3 URI list per partition', 6.2, DIMW)
t(20.6, 12.7, 'S3 Listing latency eliminated: O(N) -> O(1) lookup', 6.5, RED, bold=True)
t(20.6, 12.4, 'Query planning bottleneck removed (no live S3 API calls)', 6.5, DIMW)
t(20.6, 12.1, 'Also stores: Integrity Audit results per namespace', 6.5, DIMW)
t(20.6, 11.8, 'Phase 3 Search: SQL WHERE filter -> partition key match -> URI list', 6.5, DIMW)
t(20.6, 11.5, 'Key pattern: trident:manifest:{namespace}:{table}:{partition}', 6.5, DIMW)
t(20.6, 10.9, 'IN: Iceberg manifest files (from Nessie commit)', 6.5, RED, bold=True)
t(20.6, 10.6, 'OUT: filtered S3 URI list for matched partitions', 6.5, RED, bold=True)
t(20.6, 9.8, 'Phase 3 Search: Redis storage lookup -> S3 URIs', 6, '#a04040')

# ── Phase 3: Data Search & Delivery ─────────────────────────────────
box(6.4, 0.4, 19.2, 8.8, '#081e08', ec=GRN, lw=2.0, r=0.35)
t(16.0, 8.9, 'Phase 3  |  Data Search  &  Zero-Copy Delivery', 11, GRN, bold=True)
t(16.0, 8.5, 'Semantic Search (Milvus)  ->  LLM SQL Filter (Ollama)  ->  Storage Search (Redis)  ->  Workload Interface', 7.5, '#80c880')

# Search Pipeline
box(6.6, 5.4, 7.6, 3.2, '#041404', ec='#408040', lw=0.9, r=0.2)
t(10.4, 8.3, 'Search Pipeline', 8, GRN, bold=True)
t(10.4, 7.95, '1. User enters natural language query', 6.5, DIMW)
t(10.4, 7.65, '2. Milvus: cosine similarity -> top-5 tables', 6.5, DIMW)
t(10.4, 7.35, '3. User selects target table from candidates', 6.5, DIMW)
t(10.4, 7.05, '4. Ollama generates SQL WHERE clause', 6.5, DIMW)
t(10.4, 6.75, '   from rich_context + user condition', 6.2, DIMW)
t(10.4, 6.45, '5. Redis: partition match -> S3 URI list', 6.5, DIMW)
t(10.4, 6.15, '6. Dataset Snapshot: save for reuse', 6.5, GRN)
t(10.4, 5.6, 'IN: NL query  |  OUT: filtered S3 URI list', 6.5, GRN, bold=True)

# Workload Interfaces
box(14.4, 5.4, 11.0, 3.2, '#041404', ec='#408040', lw=0.9, r=0.2)
t(19.9, 8.3, 'Workload-Optimized Zero-Copy Interfaces', 8, GRN, bold=True)

box(14.6, 5.6, 3.3, 2.75, '#061206', ec='#306030', lw=0.7, r=0.15)
t(16.25, 8.1, 'AI  /  PyTorch / TF', 7, '#7dcea0', bold=True)
t(16.25, 7.8, 'S3 URI list injected', 6.2, DIMW)
t(16.25, 7.55, 'into Dataset SDK', 6.2, DIMW)
t(16.25, 7.3, 'Real-time S3 stream', 6.2, DIMW)
t(16.25, 7.05, 'No local copy needed', 6.2, DIMW)
t(16.25, 6.8, 'GPU starvation: zero', 6.2, GRN)
t(16.25, 6.5, 'Future: NVIDIA GDS', 5.5, '#446')
t(16.25, 5.75, 'Training workload', 6, GRN, bold=True)

box(18.1, 5.6, 3.3, 2.75, '#061206', ec='#306030', lw=0.7, r=0.15)
t(19.75, 8.1, 'HPC  /  FUSE', 7, '#7dcea0', bold=True)
t(19.75, 7.8, 'S3 URIs mounted as', 6.2, DIMW)
t(19.75, 7.55, 'virtual folder', 6.2, DIMW)
t(19.75, 7.3, '/mnt/trident/...', 6.2, DIMW)
t(19.75, 7.05, 'Legacy sim compat.', 6.2, DIMW)
t(19.75, 6.8, 'Only searched files', 6.2, GRN)
t(19.75, 6.5, 'No code changes', 5.5, '#446')
t(19.75, 5.75, 'Simulation workload', 6, GRN, bold=True)

box(21.6, 5.6, 3.6, 2.75, '#061206', ec='#306030', lw=0.7, r=0.15)
t(23.4, 8.1, 'HPDA  /  Trino SQL', 7, '#7dcea0', bold=True)
t(23.4, 7.8, 'Unified Virtual View', 6.2, DIMW)
t(23.4, 7.55, 'Cross-dataset JOINs', 6.2, DIMW)
t(23.4, 7.3, 'Structured + URI col', 6.2, DIMW)
t(23.4, 7.05, 'NL->SQL via Ollama', 6.2, DIMW)
t(23.4, 6.8, 'Iceberg connector', 6.2, GRN)
t(23.4, 6.5, 'Superset BI ready', 5.5, '#446')
t(23.4, 5.75, 'Analytics workload', 6, GRN, bold=True)

# Shared infra (EDGE 하단)
box(6.6, 0.55, 4.5, 4.6, '#101018', ec='#406080', lw=0.9, r=0.2)
t(8.85, 4.85, 'Ceph S3', 8, GRN, bold=True)
t(8.85, 4.5, 'S3-compatible Object Storage', 6.5, DIMW)
t(8.85, 4.2, 'Raw data: images/LiDAR/CSV/...', 6.5, DIMW)
t(8.85, 3.9, 'PB-scale distributed storage', 6.5, DIMW)
t(8.85, 3.55, 'Zero-Copy principle:', 6.5, GRN, bold=True)
t(8.85, 3.25, 'Files NEVER moved/copied', 6.5, DIMW)
t(8.85, 2.95, 'Only S3 URI pointers stored', 6.5, DIMW)
t(8.85, 2.6, 'S3 API: LIST for URI detect', 6.5, DIMW)
t(8.85, 2.3, 'S3 API: GET metadata only', 6.5, DIMW)
t(8.85, 1.5, 'IN/OUT: raw files (user upload)', 6, GRN, bold=True)
t(8.85, 1.2, 'OUT: S3 URIs -> Spark/FUSE/SDK', 6, GRN, bold=True)

box(11.3, 0.55, 4.8, 4.6, '#101018', ec='#8080c0', lw=0.9, r=0.2)
t(13.7, 4.85, 'Nessie', 8, '#aaaaff', bold=True)
t(13.7, 4.5, 'Iceberg Catalog  (Git-like)', 6.5, DIMW)
t(13.7, 4.2, 'Namespace + Table management', 6.5, DIMW)
t(13.7, 3.9, 'Branch / Tag / Merge support', 6.5, DIMW)
t(13.7, 3.55, 'Stores:', 6.5, '#aaaaff', bold=True)
t(13.7, 3.25, '  manifest lists + snapshot IDs', 6.2, DIMW)
t(13.7, 2.95, '  partition specs + schema history', 6.2, DIMW)
t(13.7, 2.65, '  commit lineage + data versioning', 6.2, DIMW)
t(13.7, 2.3, 'Backend: PostgreSQL (ACID)', 6.5, DIMW)
t(13.7, 1.5, 'IN: Iceberg commits from Spark', 6, '#aaaaff', bold=True)
t(13.7, 1.2, 'OUT: manifests -> Phase2, PostgreSQL', 6, '#aaaaff', bold=True)

box(16.3, 0.55, 3.8, 4.6, '#101018', ec='#608060', lw=0.9, r=0.2)
t(18.2, 4.85, 'Ollama LLM', 8, BLUE, bold=True)
t(18.2, 4.5, 'Local LLM inference', 6.5, DIMW)
t(18.2, 4.2, 'qwen2.5-coder:', 6.5, DIMW)
t(18.2, 3.9, '  Phase1: schema design', 6.2, DIMW)
t(18.2, 3.6, '  Phase2: Super Context gen', 6.2, DIMW)
t(18.2, 3.3, '  Phase3: NL->SQL WHERE', 6.2, DIMW)
t(18.2, 3.0, 'bge-m3:', 6.5, DIMW)
t(18.2, 2.7, '  Phase2: embedding for Milvus', 6.2, DIMW)
t(18.2, 2.3, 'Used across Phase 1, 2, 3', 6.5, BLUE)
t(18.2, 1.5, 'IN: schema/context/NL query', 6, BLUE, bold=True)
t(18.2, 1.2, 'OUT: schema / vector / SQL WHERE', 6, BLUE, bold=True)

box(20.3, 0.55, 5.1, 4.6, '#101018', ec='#806040', lw=0.9, r=0.2)
t(22.85, 4.85, 'Spark Operator + Trino', 8, ORG, bold=True)
t(22.85, 4.5, 'Spark: K8s-native Spark runner', 6.5, DIMW)
t(22.85, 4.2, '  SparkApplication CRD', 6.2, DIMW)
t(22.85, 3.9, '  Reads S3 / writes Iceberg', 6.2, DIMW)
t(22.85, 3.6, '  Managed by ArgoCD', 6.2, DIMW)
t(22.85, 3.25, 'Trino: Distributed SQL Engine', 6.5, DIMW)
t(22.85, 2.95, '  Iceberg connector', 6.2, DIMW)
t(22.85, 2.65, '  Unified Virtual View', 6.2, DIMW)
t(22.85, 2.35, '  NL->SQL (Ollama) + filter', 6.2, DIMW)
t(22.85, 2.05, '  Superset BI integration', 6.2, DIMW)
t(22.85, 1.5, 'Spark IN: job spec  OUT: Iceberg', 6, ORG, bold=True)
t(22.85, 1.2, 'Trino IN: SQL  OUT: result + URIs', 6, ORG, bold=True)

# Iceberg Maintenance note
box(6.6, 4.85, 19.0, 0.35, '#0a1a0a', ec='#304030', lw=0.5, r=0.1)
t(16.1, 5.02, 'Iceberg Table Maintenance  |  Compaction  |  Orphan File Removal  |  Snapshot Expiry  |  Metadata Optimization  (via Spark, triggered from Portal or on schedule)', 6, '#446')

# ═══════════════════════════════════════════════════════════════════════
# CORE
# ═══════════════════════════════════════════════════════════════════════

# FastAPI
box(26.2, 15.8, 11.4, 6.0, DIMB, ec=CYAN, lw=2.0, r=0.35)
t(31.9, 21.5, 'FastAPI  (Phase 4 Hub)', 12, CYAN, bold=True)
t(31.9, 21.1, 'Central backend for AI Prediction & 3D Twin control', 7.5, DIMW)

box(26.4, 16.0, 3.5, 5.5, '#0a1828', ec='#2a5a90', lw=0.9, r=0.2)
t(28.15, 21.2, '/api/pipeline/*', 8, BLUE, bold=True)
t(28.15, 20.85, 'Receive trigger from Portal', 6.5, DIMW)
t(28.15, 20.55, 'Submit SparkApplication CRD', 6.5, DIMW)
t(28.15, 20.25, 'to K8s Spark Operator', 6.5, DIMW)
t(28.15, 19.95, 'Return job status to Portal', 6.5, DIMW)
t(28.15, 19.65, 'Log Execution Profile:', 7, ORG, bold=True)
t(28.15, 19.35, '  dataset characteristics', 6.2, DIMW)
t(28.15, 19.05, '  stage durations (Ingest/Embed/Cache)', 6.2, DIMW)
t(28.15, 18.75, '  resource usage (CPU/Mem/S3 calls)', 6.2, DIMW)
t(28.15, 18.45, '  output metrics (partitions/vectors/keys)', 6.2, DIMW)
t(28.15, 17.85, 'OUT: profile -> PostgreSQL', 6.5, ORG, bold=True)
t(28.15, 17.55, 'OUT: CRD -> Spark Operator (K8s)', 6.5, BLUE, bold=True)
t(28.15, 17.25, 'OUT: status -> Web Portal', 6.5, DIMW)
t(28.15, 16.2, 'IN: REST POST from Web Portal', 6, CYAN, bold=True)

box(30.1, 16.0, 3.6, 5.5, '#180a28', ec='#7040c0', lw=0.9, r=0.2)
t(31.9, 21.2, '/api/simulate/*', 8, PUR, bold=True)
t(31.9, 20.85, 'Receive input profile from Portal', 6.5, DIMW)
t(31.9, 20.55, 'Query XGBoost prediction model', 6.5, DIMW)
t(31.9, 20.25, 'Return predictions:', 6.5, DIMW)
t(31.9, 19.95, '  stage durations forecast', 6.2, DIMW)
t(31.9, 19.65, '  resource usage forecast', 6.2, DIMW)
t(31.9, 19.35, '  bottleneck zone (RED/ORG/GRN)', 6.2, DIMW)
t(31.9, 19.05, 'After actual run:', 6.5, DIMW)
t(31.9, 18.75, '  compare predicted vs actual', 6.2, DIMW)
t(31.9, 18.45, '  MAPE / Precision / Recall metrics', 6.2, DIMW)
t(31.9, 17.85, 'OUT: bottleneck + resource forecast', 6.5, PUR, bold=True)
t(31.9, 17.55, '  -> Web Portal Simulation view', 6.5, DIMW)
t(31.9, 17.25, '  -> Omniverse scene overlay', 6.5, NVIDG)
t(31.9, 16.2, 'IN: REST POST from Web Portal', 6, CYAN, bold=True)

box(33.9, 16.0, 3.5, 5.5, '#082008', ec='#408040', lw=0.9, r=0.2)
t(35.65, 21.2, '/api/twin/*', 8, NVIDG, bold=True)
t(35.65, 20.85, 'Expose scene state to Kit Ext', 6.5, DIMW)
t(35.65, 20.55, 'Omniverse Kit Extension polls', 6.5, DIMW)
t(35.65, 20.25, 'this endpoint periodically', 6.5, DIMW)
t(35.65, 19.95, 'Pushes USD scene data:', 6.5, DIMW)
t(35.65, 19.65, '  node health: color + size', 6.2, DIMW)
t(35.65, 19.35, '  particle flow speed', 6.2, DIMW)
t(35.65, 19.05, '  bottleneck highlights', 6.2, DIMW)
t(35.65, 18.75, '  prediction overlay data', 6.2, DIMW)
t(35.65, 18.45, 'WebSocket: real-time push', 6.5, NVIDG)
t(35.65, 17.85, 'OUT: USD scene -> Omniverse Kit', 6.5, NVIDG, bold=True)
t(35.65, 17.55, 'IN: health data from PostgreSQL', 6.5, DIMW)
t(35.65, 17.25, 'IN: predictions from XGBoost', 6.5, DIMW)
t(35.65, 16.2, 'IN: REST/WebSocket from Kit Ext', 6, CYAN, bold=True)

# PostgreSQL
box(26.2, 9.6, 5.2, 5.9, DIMB, ec=PG, lw=1.5, r=0.3)
t(28.8, 15.2, 'PostgreSQL', 11, PG, bold=True)
t(28.8, 14.8, 'Unified CORE Database', 7.5, '#7ab8d8')
t(28.8, 14.35, 'Nessie Backend:', 7.5, '#aaaaff', bold=True)
t(28.8, 14.0, '  Iceberg table lineage', 6.5, DIMW)
t(28.8, 13.7, '  Snapshot / manifest IDs', 6.5, DIMW)
t(28.8, 13.4, '  ACID consistency (shared)', 6.5, DIMW)
t(28.8, 12.95, 'Execution Profiles:', 7.5, ORG, bold=True)
t(28.8, 12.6, '  dataset characteristics', 6.5, DIMW)
t(28.8, 12.3, '  stage durations', 6.5, DIMW)
t(28.8, 12.0, '  resource usage', 6.5, DIMW)
t(28.8, 11.7, '  output metrics', 6.5, DIMW)
t(28.8, 11.3, 'Profiles accumulate over runs', 7, PG, bold=True)
t(28.8, 11.0, '-> XGBoost training data source', 6.5, DIMW)
t(28.8, 10.7, '-> Accuracy improves over time', 6.5, DIMW)
t(28.8, 9.85, 'IN: profile writes from FastAPI', 6, PG, bold=True)
t(28.8, 9.55, 'OUT: profiles -> XGBoost training', 6, PG, bold=True)

# XGBoost
box(31.6, 9.6, 5.8, 5.9, DIMB, ec='#c03030', lw=1.5, r=0.3)
t(34.5, 15.2, 'XGBoost', 11, RED, bold=True)
t(34.5, 14.8, 'AI Prediction Model', 7.5, '#d88080')
t(34.5, 14.35, 'Feature inputs:', 7.5, DIMW, bold=True)
t(34.5, 14.0, '  file count / total size (GB)', 6.5, DIMW)
t(34.5, 13.7, '  schema complexity score', 6.5, DIMW)
t(34.5, 13.4, '  cardinality distribution', 6.5, DIMW)
t(34.5, 13.1, '  partition count / depth', 6.5, DIMW)
t(34.5, 12.75, 'Predictions:', 7.5, RED, bold=True)
t(34.5, 12.4, '  duration: Ingest/Embed/Cache', 6.5, DIMW)
t(34.5, 12.1, '  resource: CPU/Mem/S3 API calls', 6.5, DIMW)
t(34.5, 11.8, '  bottleneck zone detection', 6.5, DIMW)
t(34.5, 11.5, '  RED / ORANGE / GREEN status', 6.5, DIMW)
t(34.5, 11.1, 'Non-linear: same size data, diff', 7, RED, bold=True)
t(34.5, 10.8, 'schema complexity -> diff result', 6.5, DIMW)
t(34.5, 9.85, 'IN: input profile (features)', 6, RED, bold=True)
t(34.5, 9.55, 'OUT: bottleneck + duration + resource', 6, RED, bold=True)

# Omniverse
box(26.2, 0.4, 11.4, 8.9, DIMB, ec=NVIDG, lw=1.5, r=0.35)
t(31.9, 9.0, 'NVIDIA Omniverse Server', 11, NVIDG, bold=True)
t(31.9, 8.6, 'Nucleus  +  USD Composer  +  Kit Extension', 7.5, '#a0d060')

box(26.4, 6.5, 5.4, 2.2, '#0a1a08', ec='#408040', lw=0.8, r=0.2)
t(29.1, 8.4, 'Pipeline Twin', 8, NVIDG, bold=True)
t(29.1, 8.1, '3D spatial data flow visualization', 6.5, DIMW)
t(29.1, 7.8, 'Zones: Ingest / Metadata / Workload', 6.5, DIMW)
t(29.1, 7.5, 'Data nodes = Iceberg table assets', 6.5, DIMW)
t(29.1, 7.2, 'Particle flow = data movement', 6.5, DIMW)
t(29.1, 6.75, 'Node: GREEN/ORANGE/RED health', 6, NVIDG)

box(32.0, 6.5, 5.4, 2.2, '#0a1a08', ec='#408040', lw=0.8, r=0.2)
t(34.7, 8.4, 'Predictive Simulator', 8, NVIDG, bold=True)
t(34.7, 8.1, 'Before execution: highlight RED zones', 6.5, DIMW)
t(34.7, 7.8, 'Particle speed = predicted throughput', 6.5, DIMW)
t(34.7, 7.5, 'Scenario comparison: adjust & retry', 6.5, DIMW)
t(34.7, 7.2, 'After run: predicted vs actual MAPE', 6.5, DIMW)
t(34.7, 6.75, 'RED=bottleneck / ORG=risk / GRN=ok', 6, NVIDG)

box(26.4, 4.0, 11.0, 2.2, '#0a1a08', ec='#408040', lw=0.8, r=0.2)
t(31.9, 5.9, 'Dataset Health View', 8, NVIDG, bold=True)
t(31.9, 5.6, 'Continuous monitoring of ingested datasets (3D node color = health score)', 6.5, DIMW)
t(31.9, 5.3, 'Factors: Integrity ratio  |  Redis cache freshness  |  Search/Delivery usage  |  Partition-query alignment', 6.5, DIMW)
t(31.9, 5.0, 'Low-health -> Predictive Simulator: simulate impact of fix before applying', 6.5, NVIDG)
t(31.9, 4.25, 'Kit Extension polls FastAPI /api/twin/*  ->  USD Scene node update (color/size/flow)', 6, '#a0d060')

box(26.4, 0.6, 11.0, 3.1, '#051005', ec='#305030', lw=0.8, r=0.2)
t(31.9, 3.4, 'WebRTC Streaming  (UDP / Video)', 8, NVIDG, bold=True)
t(31.9, 3.1, 'Omniverse Streaming extension encodes 3D scene as real-time video', 6.5, DIMW)
t(31.9, 2.8, 'Delivered to Web Portal 3D Twin View via WebRTC protocol (no client install)', 6.5, DIMW)
t(31.9, 2.5, 'User interacts with 3D pipeline scene directly in browser', 6.5, DIMW)
t(31.9, 1.9, 'OUT: WebRTC (UDP/Video) -> Web Portal  3D Twin View', 7, NVIDG, bold=True)
t(31.9, 1.3, 'Kit Extension: polls /api/twin/*  ->  receives USD scene updates  ->  renders & streams', 6, '#a0d060')

# ═══════════════════════════════════════════════════════════════════════
# 화살표
# ═══════════════════════════════════════════════════════════════════════

# [1] Portal Pipeline Control -> FastAPI /api/pipeline/*
a(5.8, 20.1, 26.2, 19.5, BLUE, lw=2.5,
  lbl='REST POST /api/pipeline/trigger\n(dataset path, schema mode, params)', lo=(0, 0.4))

# [2] Portal Simulation -> FastAPI /api/simulate/*
a(5.8, 17.8, 26.2, 18.2, PUR, lw=2.5,
  lbl='REST POST /api/simulate\n(input profile: file count, size, schema complexity)', lo=(0, 0.5))

# [3] FastAPI /api/pipeline/* -> Spark Operator (K8s, EDGE 하단)
a(28.15, 15.8, 22.85, 5.2, ORG, lw=2.0, rad=0.12,
  lbl='SparkApplication CRD\n(K8s API -> Spark Operator)', lo=(-1.5, 0))

# [4] FastAPI -> PostgreSQL (profile write)
a(28.8, 15.8, 28.8, 15.5, ORG, lw=2.0,
  lbl='WRITE execution profile\n(after each pipeline run)', lo=(2.5, 0))

# [5] FastAPI /api/simulate/* -> XGBoost
a(33.7, 17.5, 33.7, 15.5, RED, lw=2.0,
  lbl='query prediction\n(input profile features)', lo=(1.8, 0))

# [6] FastAPI /api/twin/* -> Omniverse (scene update)
a(37.2, 15.8, 35.5, 9.3, NVIDG, lw=2.0, rad=-0.15,
  lbl='USD scene update\n(Kit Ext polls /api/twin/*)', lo=(1.5, 0))

# [7] PostgreSQL -> XGBoost (training data)
a(31.4, 12.5, 31.6, 12.5, YEL, lw=2.0,
  lbl='training data\n(historical execution profiles)', lo=(0, 0.45))

# [8] Nessie -> PostgreSQL (backend)  (EDGE -> CORE)
a(16.1, 2.0, 26.2, 11.5, '#aaaaff', lw=1.8, rad=-0.15,
  lbl='Nessie backend\n(ACID lineage store)', lo=(0, -0.5))

# [9] Phase 1 -> Phase 2 (vertical)
a(16.0, 15.0, 16.0, 14.7, PUR, lw=3.0,
  lbl='Iceberg manifests + schema\n-> Phase 2 Metadata Indexing', lo=(4.5, 0))

# [10] Phase 2 -> Phase 3 (vertical)
a(16.0, 9.5, 16.0, 9.25, GRN, lw=3.0,
  lbl='filtered S3 URI list\n-> Phase 3 Delivery', lo=(4.0, 0))

# [11] Ceph -> Phase 1
a(8.85, 5.15, 8.85, 15.0, GRN, lw=1.8, rad=0,
  lbl='S3 URI read (Zero-Copy)\nraw file metadata only', lo=(-2.2, 0))

# [12] Phase 1 -> Nessie
a(16.0, 15.0, 13.7, 5.15, '#aaaaff', lw=1.8, rad=0.15,
  lbl='Iceberg commit\n(table metadata)', lo=(1.5, 0))

# [13] Execution profile logging: FastAPI intercepts pipeline completion
a(26.2, 17.5, 6.0, 17.5, ORG, lw=1.5, rad=0.2,
  lbl='Execution profile captured\n(dataset chars, stage duration, resource, output metrics)', lo=(0, 0.6))

# [14] Omniverse -> Web Portal (WebRTC)
a(26.2, 1.8, 5.8, 14.9, NVIDG, lw=2.5, rad=0.2,
  lbl='WebRTC streaming\n(UDP/Video)\n3D Twin View', lo=(-1.2, 0))

# [15] Ollama -> Phases (schema, embed, SQL)
a(18.2, 5.15, 13.0, 15.0, BLUE, lw=1.5, rad=-0.15,
  lbl='AI schema design\nSuper Context embedding\nNL->SQL WHERE clause', lo=(-2.5, 0))

# [16] Trino -> Phase 3 HPDA
a(22.85, 5.15, 23.4, 5.6, ORG, lw=1.5,
  lbl='unified SQL\n(HPDA interface)', lo=(0, 0.4))

# [17] ArgoCD -> EDGE pods
a(5.8, 9.0, 6.4, 9.0, RED, lw=2.0,
  lbl='K8s manifest deploy\n(all pipeline pods)', lo=(0, 0.45))

# [18] Git -> ArgoCD (poll)
a(3.1, 2.75, 3.1, 0.55, RED, lw=1.5, rad=0,
  lbl='GitOps poll', lo=(0.9, 0))

# [19] Phase2 Milvus <-> Phase2 Redis 구분 화살표 (내부, 실선으로 흐름 표시)
# 없어도 박스 설명으로 충분

# ═══════════════════════════════════════════════════════════════════════
plt.tight_layout(pad=0.1)
plt.savefig('/home/netai/chang/overview_v2.png', dpi=150, bbox_inches='tight',
            facecolor=fig.get_facecolor())
print("saved.")
