#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found. Creating one..."
    python3 fix_env.py
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

echo "[INFO] Checking MySQL server..."
if ! lsof -iTCP:3306 -sTCP:LISTEN >/dev/null 2>&1; then
    echo "[WARN] MySQL is not listening on port 3306. Trying to start it..."
    if command -v brew >/dev/null 2>&1; then
        brew services start mysql >/dev/null 2>&1 || true
    fi
    if command -v mysql.server >/dev/null 2>&1; then
        mysql.server start >/dev/null 2>&1 || true
    fi
    sleep 2
    if ! lsof -iTCP:3306 -sTCP:LISTEN >/dev/null 2>&1; then
        echo "[ERROR] MySQL still not running. Start it manually, then re-run start.sh."
        exit 1
    fi
fi

echo "[INFO] Starting server..."
python3 run.py
