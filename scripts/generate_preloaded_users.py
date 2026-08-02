#!/usr/bin/env python3
"""Generate a protected deployment credential manifest for Umoja Afya users.

Passwords are generated at deployment time, never embedded in source, UI, Docker
Compose, or release archives. All generated accounts must change their password
at first sign-in and are MFA-required.
"""
from __future__ import annotations

import argparse
import json
import secrets
import string
from pathlib import Path

COUNTRIES = {
    "TZ": {"facility": "MNH-UPANGA", "label": "Tanzania"},
    "KE": {"facility": "KE-KNH", "label": "Kenya"},
    "NG": {"facility": "NG-NHA", "label": "Nigeria"},
    "PK": {"facility": "PK-PIMS", "label": "Pakistan"},
    "RW": {"facility": "RW-CHUK", "label": "Rwanda"},
}
ROLE_USERS = [
    ("admin", "Country ICT Administrator"),
    ("registration", "Registration Officer"),
    ("physician", "Medical Officer"),
    ("nurse", "Registered Nurse"),
    ("pharmacy", "Pharmacist"),
    ("laboratory", "Laboratory Scientist"),
    ("finance", "Revenue Cycle Officer"),
    ("operations", "Hospital Operations Officer"),
]


def strong_password(length: int = 22) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%*-_=+"
    while True:
        value = "".join(secrets.choice(alphabet) for _ in range(length))
        if (any(c.islower() for c in value) and any(c.isupper() for c in value)
                and any(c.isdigit() for c in value) and any(not c.isalnum() for c in value)):
            return value


def build_manifest() -> dict:
    users = [{
        "username": "platform.admin",
        "display_name": "Umoja Afya Global Superuser",
        "role_code": "admin",
        "country_codes": sorted(COUNTRIES),
        "all_facilities_in_countries": True,
        "superuser": True,
        "password": strong_password(),
    }]
    for country, meta in COUNTRIES.items():
        prefix = country.lower()
        for role, title in ROLE_USERS:
            users.append({
                "username": f"{prefix}.{role}",
                "display_name": f"{meta['label']} {title}",
                "role_code": role,
                "country_codes": [country],
                "facility_codes": [meta["facility"]],
                "all_facilities_in_countries": role == "admin",
                "password": strong_password(),
            })
    return {
        "schema_version": 2,
        "generated_notice": "Deployment-generated initial credentials. Store in an approved password vault, distribute individually, and require password change plus MFA enrollment.",
        "users": users,
    }


def upgrade_manifest(data: dict) -> tuple[dict, bool]:
    """Upgrade an existing roster without replacing any stored passwords."""
    users = data.get("users") if isinstance(data, dict) else None
    if not isinstance(users, list) or not users:
        raise SystemExit("Existing preloaded-user manifest is invalid; move it aside and rerun initialization")
    changed = int(data.get("schema_version", 0)) < 2
    global_user = next((item for item in users if str(item.get("username", "")).lower() == "platform.admin"), None)
    if global_user is None:
        global_user = {
            "username": "platform.admin",
            "display_name": "Umoja Afya Global Superuser",
            "role_code": "admin",
            "country_codes": sorted(COUNTRIES),
            "all_facilities_in_countries": True,
            "superuser": True,
            "password": strong_password(),
        }
        users.insert(0, global_user)
        changed = True
    expected = {
        "display_name": "Umoja Afya Global Superuser",
        "role_code": "admin",
        "country_codes": sorted(COUNTRIES),
        "all_facilities_in_countries": True,
        "superuser": True,
    }
    for key, value in expected.items():
        if global_user.get(key) != value:
            global_user[key] = value
            changed = True
    data["schema_version"] = 2
    data["generated_notice"] = "Deployment-generated initial credentials. Store in an approved password vault, distribute individually, and require password change plus MFA enrollment."
    return data, changed


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists() and output.stat().st_size and not args.force:
        data, changed = upgrade_manifest(json.loads(output.read_text(encoding="utf-8")))
        if not changed:
            print(f"Preserved existing preloaded-user manifest: {output}")
            return
        output.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        try:
            output.chmod(0o600)
        except OSError:
            pass
        print(f"Upgraded the protected preloaded-user manifest without changing existing passwords: {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_manifest(), indent=2) + "\n", encoding="utf-8")
    try:
        output.chmod(0o600)
    except OSError:
        pass
    print(f"Generated protected deployment credentials for preloaded users: {output}")


if __name__ == "__main__":
    main()
