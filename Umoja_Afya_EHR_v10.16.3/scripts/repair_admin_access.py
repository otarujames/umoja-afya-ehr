#!/usr/bin/env python3
"""Repair baseline administrator country, facility, function and department matrices.

This is safe to run repeatedly. It does not change passwords unless --reset-passwords
is explicitly supplied together with the deployment credential manifest.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from sqlalchemy import delete, select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.access_control import ROLE_TEMPLATES, replace_user_access
from backend.app.audit import write_audit
from backend.app.database import SessionLocal
from backend.app.enterprise_models import UserAccount
from backend.app.models import Facility
from backend.app.security import hash_password, password_is_strong
from backend.app.operational_models import UserSession

ADMIN_COUNTRIES = {
    "platform.admin": None,
    "tz.admin": ["TZ"],
    "ke.admin": ["KE"],
    "ng.admin": ["NG"],
    "pk.admin": ["PK"],
    "rw.admin": ["RW"],
}


def manifest_passwords() -> dict[str, str]:
    path = os.getenv("UMOJA_PRELOADED_USERS_FILE", "").strip()
    if not path or not Path(path).is_file():
        return {}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {str(x["username"]).lower(): str(x["password"]) for x in data.get("users", [])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-passwords", action="store_true")
    args = parser.parse_args()
    passwords = manifest_passwords() if args.reset_passwords else {}
    repaired = 0
    with SessionLocal() as db:
        facilities = list(db.scalars(select(Facility).where(Facility.active.is_(True))).all())
        by_country: dict[str, list[str]] = {}
        for facility in facilities:
            by_country.setdefault(facility.country_code, []).append(facility.code)
        missing = {"TZ", "KE", "NG", "PK", "RW"} - set(by_country)
        if missing:
            raise SystemExit(f"Missing country facility directories: {', '.join(sorted(missing))}")

        template = ROLE_TEMPLATES["admin"]
        for username, fixed_countries in ADMIN_COUNTRIES.items():
            user = db.scalar(select(UserAccount).where(UserAccount.username == username))
            if not user:
                print(f"Skipped missing account: {username}")
                continue
            countries = sorted(by_country) if fixed_countries is None else fixed_countries
            facility_codes = sorted({code for country in countries for code in by_country[country]})
            user.role_code = "admin"
            user.active = True
            user.requires_mfa = True
            if user.facility_code not in facility_codes:
                user.facility_code = facility_codes[0]
            replace_user_access(
                db,
                user,
                functions=template["functions"],
                departments=template["departments"],
                facilities=facility_codes,
                countries=countries,
                actor="Administrator Access Repair",
                reason="Repair full administrator matrix and country isolation",
            )
            if args.reset_passwords and username in passwords:
                password = passwords[username]
                if not password_is_strong(password):
                    raise SystemExit(f"Manifest password does not meet policy: {username}")
                user.password_hash = hash_password(password)
                user.failed_login_count = 0
                user.locked_until = None
                user.must_change_password = True
                db.execute(delete(UserSession).where(UserSession.user_account_id == user.id))
            write_audit(
                db,
                action="REPAIR_ADMIN_ACCESS_MATRIX",
                resource_type="UserAccount",
                resource_id=user.user_id,
                actor="Administrator Access Repair",
                role="system.users.manage",
                facility_code=user.facility_code,
                details=f"username={username}; countries={','.join(countries)}; facilities={len(facility_codes)}; full_functions={len(template['functions'])}; password_reset={args.reset_passwords and username in passwords}",
            )
            repaired += 1
        db.commit()
    print(f"Repaired {repaired} administrator account(s).")


if __name__ == "__main__":
    main()
