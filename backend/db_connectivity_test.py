#!/usr/bin/env python3
"""Systematic DB connectivity diagnostics for local development."""

import os
import socket
from pathlib import Path

try:
    import pymysql
except Exception as exc:  # pragma: no cover
    print(f"[FAIL] Import pymysql failed: {exc}")
    raise


def load_env(env_path: Path) -> None:
    if not env_path.exists():
        print(f"[WARN] .env not found at {env_path}")
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def main() -> int:
    base = Path(__file__).resolve().parent
    load_env(base / ".env")

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    db_name = os.getenv("DB_NAME", "teaching_system")

    print("[INFO] DB config in use:")
    print(f"  host={host}")
    print(f"  port={port}")
    print(f"  user={user}")
    print(f"  db={db_name}")

    try:
        ip = socket.gethostbyname(host)
        print(f"[PASS] DNS resolved: {host} -> {ip}")
    except Exception as exc:
        print(f"[FAIL] DNS resolution failed for {host}: {exc}")
        return 2

    try:
        with socket.create_connection((host, port), timeout=3):
            print(f"[PASS] TCP connect success: {host}:{port}")
    except Exception as exc:
        print(f"[FAIL] TCP connect failed: {host}:{port} ({exc})")
        return 3

    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=db_name,
            connect_timeout=5,
            read_timeout=5,
            write_timeout=5,
            charset="utf8mb4",
        )
        with conn.cursor() as cur:
            cur.execute("SELECT VERSION()")
            version = cur.fetchone()[0]
        conn.close()
        print(f"[PASS] MySQL auth/query success, version={version}")
        return 0
    except Exception as exc:
        print(f"[FAIL] MySQL auth/query failed: {exc}")
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
