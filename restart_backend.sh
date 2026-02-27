#!/bin/bash
set -euo pipefail
# ─────────────────────────────────────────────────────────────────────────────
# GenXSOP — Backend Restart Script
# Usage: ./restart_backend.sh [port]
# Default port: 8000
# ─────────────────────────────────────────────────────────────────────────────

PORT=${1:-8000}
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(cd "$(dirname "$0")/backend" && pwd)"
LOG_FILE="$BACKEND_DIR/server.log"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  GenXSOP Backend Restart"
echo "  Port: $PORT"
echo "  Dir:  $BACKEND_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Kill any process using the port ───────────────────────────────────
echo ""
echo "▶ Stopping any process on port $PORT..."
PIDS=$(lsof -ti tcp:$PORT 2>/dev/null || true)
if [ -n "$PIDS" ]; then
    echo "  Killing PIDs: $PIDS"
    echo "$PIDS" | xargs kill -9 2>/dev/null
    sleep 1
    echo "  ✓ Port $PORT is now free"
else
    echo "  ✓ Port $PORT was already free"
fi

# ── Step 2: Change to backend directory ──────────────────────────────────────
cd "$BACKEND_DIR" || { echo "ERROR: Cannot cd to $BACKEND_DIR"; exit 1; }

# ── Step 3: Detect Python ────────────────────────────────────────────────────
if [ -x "$ROOT_DIR/venv/bin/python" ]; then
    PYTHON="$ROOT_DIR/venv/bin/python"
elif [ -x "$BACKEND_DIR/venv/bin/python" ]; then
    PYTHON="$BACKEND_DIR/venv/bin/python"
elif command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "ERROR: Python not found. Please install Python 3.10+"
    exit 1
fi

echo ""
echo "▶ Using Python: $($PYTHON --version) ($PYTHON)"

# ── Step 4: Check if uvicorn is available ────────────────────────────────────
if ! $PYTHON -m uvicorn --version &>/dev/null; then
    echo ""
    echo "▶ uvicorn not found. Installing requirements..."
    $PYTHON -m pip install -r requirements.txt
fi

# ── Step 4b: Ensure pydantic email validator optional dep is present ─────────
if ! $PYTHON -c "import email_validator" &>/dev/null; then
    echo ""
    echo "▶ email-validator missing. Installing..."
    $PYTHON -m pip install email-validator
fi

# ── Step 5: Validate app imports ─────────────────────────────────────────────
echo ""
echo "▶ Validating app imports..."
if $PYTHON -c "from app.main import app; print('  ✓ Import OK')" 2>&1; then
    :
else
    echo "  ✗ Import failed. Check errors above."
    exit 1
fi

# ── Step 6: Start the server ─────────────────────────────────────────────────
echo ""
echo "▶ Starting GenXSOP backend on port $PORT..."
echo "  Logs: $LOG_FILE"
echo ""

$PYTHON -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --reload \
    --log-level info \
    2>&1 | tee "$LOG_FILE"
