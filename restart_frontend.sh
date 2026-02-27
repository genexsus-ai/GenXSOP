#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# GenXSOP — Frontend Restart Script
# Usage: ./restart_frontend.sh [port]
# Default port: 5173
# ─────────────────────────────────────────────────────────────────────────────

PORT=${1:-5173}
FRONTEND_DIR="$(cd "$(dirname "$0")/frontend" && pwd)"
URL="http://localhost:$PORT"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  GenXSOP Frontend Restart"
echo "  Port: $PORT"
echo "  Dir:  $FRONTEND_DIR"
echo "  URL:  $URL"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ── Step 1: Kill any process using the port ───────────────────────────────────
echo ""
echo "▶ Stopping any process on port $PORT..."
PIDS=$(lsof -ti tcp:$PORT 2>/dev/null)
if [ -n "$PIDS" ]; then
    echo "  Killing PIDs: $PIDS"
    echo "$PIDS" | xargs kill -9 2>/dev/null
    sleep 1
    echo "  ✓ Port $PORT is now free"
else
    echo "  ✓ Port $PORT was already free"
fi

# ── Step 2: Change to frontend directory ─────────────────────────────────────
cd "$FRONTEND_DIR" || { echo "ERROR: Cannot cd to $FRONTEND_DIR"; exit 1; }

# ── Step 3: Check node_modules ───────────────────────────────────────────────
if [ ! -d "node_modules" ]; then
    echo ""
    echo "▶ node_modules not found. Installing dependencies..."
    npm install
fi

# ── Step 4: Open browser after a short delay ─────────────────────────────────
echo ""
echo "▶ Starting Vite dev server on port $PORT..."
echo "  Opening $URL in browser in 3 seconds..."
echo ""

# Open browser after 3 seconds in background
(sleep 3 && open "$URL") &

# ── Step 5: Start Vite dev server ────────────────────────────────────────────
# Force IPv4 host to avoid some macOS localhost/IPv6 resolution hangs.
npm run dev -- --host 127.0.0.1 --port $PORT
