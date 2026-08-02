#!/usr/bin/env python3
"""Idempotently provision deployment-generated administrator and operational users."""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.access_control import ROLE_TEMPLATES, replace_user_access  # noqa: E402
from backend.app.audit import write_audit  # noqa: E402
from backend.app.database import SessionLocal  # noqa: E402
from backend.app.enterprise_models import UserAccount  # noqa: E402
from backend.app.models import Facility  # noqa: E402
from backend.app.security import hash_password, password_is_strong  # noqa: E402


def load_manifest() -> tuple[Path, dict] | None:
    value = os.getenv("UMOJA_PRELOADED_USERS_FILE", "").strip()
    if not value:
        print("Preloaded-user provisioning is not configured; skipping.")
        return None
    path = Path(value)
    if not path.is_file():
        raise SystemExit(f"Configured preloaded-user manifest does not exist: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data.get("users"), list) or not data["users"]:
        raise SystemExit("Preloaded-user manifest has no users")
    return path, data


def main() -> None:
    loaded = load_manifest()
    if not loaded:
        return
    path, data = loaded
    superusers = [item for item in data["users"] if item.get("superuser")]
    if len(superusers) != 1:
        raise SystemExit("The deployment roster must contain exactly one manifest-designated global superuser")
    created = updated = 0
    with SessionLocal() as db:
        facilities = list(db.scalars(select(Facility).where(Facility.active.is_(True))).all())
        by_code = {item.code: item for item in facilities}
        by_country: dict[str, list[str]] = {}
        for item in facilities:
            by_country.setdefault(item.country_code, []).append(item.code)

        for spec in data["users"]:
            username = str(spec["username"]).strip().lower()
            password = str(spec["password"])
            role = str(spec.get("role_code", "custom")).strip().lower()
            is_superuser = bool(spec.get("superuser"))
            countries = sorted({str(code).strip().upper() for code in spec.get("country_codes", [])})
            if role not in ROLE_TEMPLATES:
                raise SystemExit(f"Unknown role template for {username}: {role}")
            if not password_is_strong(password):
                raise SystemExit(f"Generated temporary password failed strength policy for {username}")
            if not countries:
                raise SystemExit(f"No country context assigned for {username}")
            missing_countries = [code for code in countries if code not in by_country]
            if missing_countries:
                raise SystemExit(f"Country facility directory is not loaded for {username}: {', '.join(missing_countries)}")

            requested = [str(code).strip().upper() for code in spec.get("facility_codes", [])]
            if spec.get("all_facilities_in_countries"):
                requested = sorted({code for country in countries for code in by_country[country]})
            if not requested:
                requested = [by_country[countries[0]][0]]
            invalid = [code for code in requested if code not in by_code or by_code[code].country_code not in countries]
            if invalid:
                raise SystemExit(f"Invalid or cross-country facilities for {username}: {', '.join(invalid)}")

            user = db.scalar(select(UserAccount).where(UserAccount.username == username))
            if not user:
                user = UserAccount(
                    username=username,
                    display_name=str(spec["display_name"]).strip(),
                    role_code=role,
                    facility_code=requested[0],
                    password_hash=hash_password(password),
                    active=True,
                    requires_mfa=True,
                    must_change_password=True,
                    password_changed_at=datetime.now(timezone.utc),
                )
                db.add(user)
                db.flush()
                created += 1
            else:
                # Preserve an existing password during normal restart/upgrade, while
                # always repairing authoritative identity and access metadata.
                user.display_name = str(spec["display_name"]).strip()
                user.role_code = role
                user.active = True
                user.requires_mfa = True
                if user.facility_code not in requested:
                    user.facility_code = requested[0]
                updated += 1

            # Deployment baseline administrators must never inherit a stale
            # custom matrix. The manifest-designated global superuser receives
            # every active country, facility, function and department.
            if is_superuser:
                role = "admin"
                countries = sorted(by_country)
                requested = sorted({code for country in countries for code in by_country[country]})
                user.role_code = "admin"
            elif username.endswith(".admin") and username.split(".", 1)[0].upper() in by_country:
                role = "admin"
                country = username.split(".", 1)[0].upper()
                countries = [country]
                requested = sorted(by_country[country])
                user.role_code = "admin"

            template = ROLE_TEMPLATES[role]
            replace_user_access(
                db,
                user,
                functions=template["functions"],
                departments=template["departments"],
                facilities=requested,
                countries=countries,
                actor="Deployment Provisioner",
                reason="Deployment-generated baseline user roster",
            )
            write_audit(
                db,
                action="PRELOAD_USER_ACCOUNT" if user.last_login_at is None else "SYNCHRONIZE_PRELOADED_USER_ACCESS",
                resource_type="UserAccount",
                resource_id=user.user_id,
                actor="Deployment Provisioner",
                role="system.users.manage",
                facility_code=user.facility_code,
                details=f"username={username}; role={role}; superuser={is_superuser}; countries={','.join(countries)}; facilities={len(requested)}",
            )
        db.commit()
    print(f"Preloaded user roster synchronized from {path}: {created} created, {updated} existing accounts preserved.")


if __name__ == "__main__":
    main()
