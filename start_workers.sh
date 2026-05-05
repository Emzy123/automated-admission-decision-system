#!/usr/bin/env bash
# ============================================================
# start_workers.sh
# Starts the Celery worker and optional Flower monitor
# Usage:
#   bash start_workers.sh          # Worker only
#   bash start_workers.sh --flower # Worker + Flower UI on :5555
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtualenv if present
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "==> Starting Celery worker..."
celery -A celery_worker.celery worker --loglevel=info &
WORKER_PID=$!
echo "    Worker PID: $WORKER_PID"

if [[ "$1" == "--flower" ]]; then
    echo "==> Starting Flower monitoring UI on http://localhost:5555 ..."
    celery -A celery_worker.celery flower --port=5555 &
    FLOWER_PID=$!
    echo "    Flower PID: $FLOWER_PID"
fi

echo ""
echo "Workers running. Press CTRL+C to stop."
wait
