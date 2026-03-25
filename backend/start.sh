#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found. Creating one..."
    python3 fix_env.py
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

echo "[INFO] Starting server..."
python3 run.py