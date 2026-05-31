#!/usr/bin/env bash
# Run twin-hub in live mode against the Trident stats-service.
#
# Usage (from the Trident-Twin repo root on l40s):
#   cd /mnt/Trident-Twin-520d314/twin-hub
#   bash run_live.sh
#
# Or with a bearer token:
#   TRIDENT_STATS_TOKEN=<token> bash run_live.sh
#
# The stats-service ClusterIP is stable at 10.234.33.83 (port 80).
# twin-hub listens on port 8765; the Isaac Sim extension default is http://localhost:8765.

set -euo pipefail

STATS_URL="${TRIDENT_STATS_BASE_URL:-http://10.234.33.83}"
PORT="${TWIN_HUB_PORT:-8765}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[twin-hub] stats-service → ${STATS_URL}"
echo "[twin-hub] listening on   → 0.0.0.0:${PORT}"

cd "${SCRIPT_DIR}"

TRIDENT_STATS_BASE_URL="${STATS_URL}" \
  uvicorn app:app \
    --host 0.0.0.0 \
    --port "${PORT}" \
    --log-level info
