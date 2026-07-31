#!/usr/bin/env python3
"""Validate runtime settings, wait for PostgreSQL and apply controlled migrations."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.config import ConfigurationError, get_settings  # noqa: E402
from backend.app.database import engine  # noqa: E402


def wait_for_database(timeout: int) -> None:
    deadline = time.monotonic() + timeout
    attempt = 0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        attempt += 1
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            print(f"Database is available after {attempt} attempt(s).", flush=True)
            return
        except Exception as exc:  # noqa: BLE001 - retry boundary
            last_error = exc
            sleep_for = min(1 + attempt, 5)
            print(f"Waiting for database (attempt {attempt}): {type(exc).__name__}", flush=True)
            time.sleep(sleep_for)
    raise SystemExit(f"Database did not become ready within {timeout} seconds: {last_error}")


def run_migrations() -> None:
    if engine.dialect.name != "postgresql":
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)
        return

    # A session-level advisory lock prevents simultaneous replicas from racing
    # Alembic at startup. The lock is automatically released on disconnect.
    with engine.connect() as lock_connection:
        lock_connection.execute(text("SELECT pg_advisory_lock(772026100)"))
        try:
            subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT, check=True)
        finally:
            lock_connection.execute(text("SELECT pg_advisory_unlock(772026100)"))
            lock_connection.commit()


def run_script(name: str) -> None:
    subprocess.run([sys.executable, str(ROOT / "scripts" / name)], cwd=ROOT, check=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["review", "production"], required=True)
    parser.add_argument("--database-timeout", type=int, default=int(os.getenv("UMOJA_DB_STARTUP_TIMEOUT", "180")))
    args = parser.parse_args()

    settings = get_settings()
    try:
        settings.validate_runtime()
    except ConfigurationError as exc:
        raise SystemExit(f"Deployment configuration error: {exc}") from exc

    if settings.environment.lower() != args.mode:
        raise SystemExit(f"Prestart mode '{args.mode}' does not match UMOJA_ENVIRONMENT='{settings.environment}'.")

    run_script("check_migrations.py")
    wait_for_database(args.database_timeout)
    run_migrations()

    if args.mode == "review":
        run_script("seed_review_data.py")
    else:
        run_script("bootstrap_reference_data.py")
    run_script("sanitize_legacy_accounts.py")
    run_script("preload_users.py")

    print(f"Umoja Afya {args.mode} prestart completed successfully.", flush=True)


if __name__ == "__main__":
    main()
