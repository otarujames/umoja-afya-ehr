from __future__ import annotations

import argparse
import getpass
import os
import sys
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal  # noqa: E402
from backend.app.enterprise_models import UserAccount  # noqa: E402
from backend.app.security import hash_password, password_is_strong  # noqa: E402



def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update the first Umoja Afya administrator.")
    parser.add_argument("--username", required=True)
    parser.add_argument("--display-name", required=True)
    parser.add_argument("--facility", required=True)
    parser.add_argument("--password", default=None, help="Omit to enter securely at the terminal")
    parser.add_argument("--force-reset", action="store_true", default=os.getenv("UMOJA_BOOTSTRAP_ADMIN_FORCE_RESET", "false").lower() in {"1", "true", "yes"})
    args = parser.parse_args()

    password = args.password or getpass.getpass("Administrator password: ")
    if not password_is_strong(password):
        raise SystemExit("Password must be at least 12 characters and include upper, lower, number and symbol.")
    if password in {"change-this-before-production"}:
        raise SystemExit("A demonstration or placeholder password cannot be used in production.")

    username = args.username.lower().strip()
    with SessionLocal() as db:
        user = db.scalar(select(UserAccount).where(UserAccount.username == username))
        if user and not args.force_reset:
            print(f"Administrator '{username}' already exists; no change made.")
            return
        if not user:
            user = UserAccount(
                username=username,
                display_name=args.display_name,
                role_code="admin",
                facility_code=args.facility,
                password_hash=hash_password(password),
                active=True,
                requires_mfa=True,
            )
            db.add(user)
            action = "created"
        else:
            user.display_name = args.display_name
            user.facility_code = args.facility
            user.role_code = "admin"
            user.password_hash = hash_password(password)
            user.active = True
            user.requires_mfa = True
            action = "updated"
        db.commit()
        print(f"Administrator '{username}' {action}. Configure government SSO/MFA before clinical go-live.")


if __name__ == "__main__":
    main()
