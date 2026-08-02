#!/usr/bin/env python3
"""Generate a protected one-time credential manifest for standard Umoja Afya users.

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
        "display_name": "Umoja Afya Platform Administrator",
        "role_code": "admin",
        "country_codes": sorted(COUNTRIES),
        "all_facilities_in_countries": True,
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
        "schema_version": 1,
        "generated_notice": "One-time temporary credentials. Store securely, distribute individually, and delete after first use.",
        "users": users,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists() and output.stat().st_size and not args.force:
        print(f"Preserved existing preloaded-user manifest: {output}")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(build_manifest(), indent=2) + "\n", encoding="utf-8")
    try:
        output.chmod(0o600)
    except OSError:
        pass
    print(f"Generated protected one-time credentials for preloaded users: {output}")


if __name__ == "__main__":
    main()
