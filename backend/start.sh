#!/bin/bash
cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "[INFO] Virtual environment not found. Creating one..."
    python3 fix_env.py
fi

echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Ensure local DB/API traffic is not routed through proxy.
export NO_PROXY="${NO_PROXY:-localhost,127.0.0.1,::1}"
export no_proxy="${no_proxy:-localhost,127.0.0.1,::1}"

if [ -f ".env" ]; then
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
fi

DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-3306}"

is_mysql_ready() {
    python3 - <<'PY' >/dev/null 2>&1
import os
import socket
import sys

host = os.getenv("DB_HOST", "localhost")
port = int(os.getenv("DB_PORT", "3306"))
user = os.getenv("DB_USER", "root")
password = os.getenv("DB_PASSWORD", "")
database = os.getenv("DB_NAME", "teaching_system")

try:
    with socket.create_connection((host, port), timeout=2):
        pass
except Exception:
    sys.exit(1)

try:
    import pymysql
    conn = pymysql.connect(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        connect_timeout=3,
        read_timeout=3,
        write_timeout=3,
        charset="utf8mb4",
    )
    conn.close()
except Exception:
    sys.exit(1)

sys.exit(0)
PY
}

echo "[INFO] Checking MySQL server..."
if ! is_mysql_ready; then
    echo "[WARN] MySQL is not reachable at ${DB_HOST}:${DB_PORT}. Trying to start it..."
    if command -v brew >/dev/null 2>&1; then
        brew services start mysql >/dev/null 2>&1 || true
        brew services start mysql@8.0 >/dev/null 2>&1 || true
    fi
    if command -v mysql.server >/dev/null 2>&1; then
        mysql.server start >/dev/null 2>&1 || true
    fi
    sleep 3
    if ! is_mysql_ready; then
        echo "[ERROR] MySQL still not reachable at ${DB_HOST}:${DB_PORT}. Start it manually, then re-run start.sh."
        exit 1
    fi
fi

echo "[INFO] Starting server..."
python3 run.py
