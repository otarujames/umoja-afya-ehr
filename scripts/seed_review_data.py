#!/usr/bin/env python3
"""Idempotently seed the Docker review environment after Alembic migrations."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal
from backend.app.seed import seed_database
from backend.app import enhancement_models, enterprise_models, operational_models  # noqa: F401


def main() -> None:
    with SessionLocal() as db:
        seed_database(db)
    print("Umoja Afya Docker review data is ready (10,000 synthetic patients).")


if __name__ == "__main__":
    main()
