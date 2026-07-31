#!/usr/bin/env python3
"""Import an approved Tanzania HFR master-facility export into Umoja Afya.

Supports CSV, JSON and YAML. The script uses the audited /facilities/import-hfr API,
so imported facilities are immediately available in Change Context and, by default,
are granted to active system-administrator accounts.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import httpx
import yaml

ALIASES = {
    "code": ["code", "facility_code", "facility code", "facility_identifier_number", "facility identifier number"],
    "hfr_code": ["hfr_code", "hfr code", "facility_identifier_number", "facility identifier number", "facility code"],
    "name": ["name", "facility_name", "facility name", "registered_name", "registered name"],
    "facility_type": ["facility_type", "facility type", "type"],
    "region": ["region", "region_name", "region name"],
    "council": ["council", "council_name", "council name", "district", "district/council"],
    "ownership_category": ["ownership_category", "ownership category", "ownership"],
    "ownership_authority": ["ownership_authority", "ownership authority", "authority"],
    "hierarchy_level": ["hierarchy_level", "hierarchy level", "level"],
    "parent_code": ["parent_code", "parent code"],
    "relation": ["relation"],
}


def norm_key(value: str) -> str:
    return " ".join(value.strip().lower().replace("_", " ").replace("-", " ").split())


def pick(row: dict[str, Any], field: str, default: Any = None) -> Any:
    normalized = {norm_key(str(k)): v for k, v in row.items()}
    for alias in ALIASES[field]:
        value = normalized.get(norm_key(alias))
        if value not in (None, ""):
            return value
    return default


def infer_level(facility_type: str) -> str:
    text = facility_type.lower()
    if "national" in text:
        return "National"
    if "zonal" in text:
        return "Zonal"
    if "regional" in text:
        return "Regional"
    if "district" in text:
        return "District"
    if "health cent" in text:
        return "Health Centre"
    if "dispens" in text:
        return "Dispensary"
    return "Other"


def load_rows(path: Path) -> list[dict[str, Any]]:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return list(csv.DictReader(handle))
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if suffix in {".yml", ".yaml"} else json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("facilities", data.get("items", data.get("data", [])))
    if not isinstance(data, list):
        raise ValueError("Expected a list of facility records or an object containing facilities/items/data.")
    return [dict(item) for item in data]


def normalize(row: dict[str, Any], public_only: bool) -> dict[str, Any] | None:
    name = str(pick(row, "name", "")).strip()
    hfr_code = str(pick(row, "hfr_code", "")).strip() or None
    code = str(pick(row, "code", hfr_code or "")).strip()
    facility_type = str(pick(row, "facility_type", "Health Facility")).strip()
    ownership_category = str(pick(row, "ownership_category", "Public")).strip()
    ownership_authority = str(pick(row, "ownership_authority", "Government")).strip()
    public_terms = f"{ownership_category} {ownership_authority}".lower()
    if public_only and not any(term in public_terms for term in ("public", "moh", "lga", "military", "police", "prison", "government", "mda")):
        return None
    if not code or not name:
        return None
    return {
        "code": code,
        "hfr_code": hfr_code,
        "name": name,
        "facility_type": facility_type,
        "region": str(pick(row, "region", "")).strip() or None,
        "council": str(pick(row, "council", "")).strip() or None,
        "ownership_category": ownership_category or "Public",
        "ownership_authority": ownership_authority or None,
        "hierarchy_level": str(pick(row, "hierarchy_level", infer_level(facility_type))).strip() or infer_level(facility_type),
        "parent_code": str(pick(row, "parent_code", "")).strip() or None,
        "relation": str(pick(row, "relation", "Government health system")).strip(),
    }


def chunks(items: list[dict[str, Any]], size: int = 1000):
    for index in range(0, len(items), size):
        yield items[index:index + size]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", type=Path, help="Approved HFR CSV, JSON or YAML export")
    parser.add_argument("--base-url", default="http://localhost:8000/api/v1")
    parser.add_argument("--username", required=True, help="Authorized institutional username; no default is provided")
    parser.add_argument("--password", required=True, help="Password for an authorized institutional account; no default is provided")
    parser.add_argument("--include-private", action="store_true")
    parser.add_argument("--source", default="Approved Tanzania HFR master-facility export")
    args = parser.parse_args()

    raw = load_rows(args.file)
    facilities = [item for row in raw if (item := normalize(row, public_only=not args.include_private))]
    if not facilities:
        raise SystemExit("No valid facilities found in the input file.")

    session = httpx.Client()
    login = session.post(f"{args.base_url.rstrip('/')}/auth/login", json={"username": args.username, "password": args.password}, timeout=30)
    login.raise_for_status()
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    totals = {"inserted": 0, "updated": 0, "total_processed": 0, "system_admin_facility_grants": 0}
    for batch in chunks(facilities):
        response = session.post(
            f"{args.base_url.rstrip('/')}/facilities/import-hfr",
            headers=headers,
            json={
                "facilities": batch,
                "actor": args.username,
                "source_system": args.source,
                "grant_to_system_admins": True,
            },
            timeout=120,
        )
        response.raise_for_status()
        result = response.json()
        for key in totals:
            totals[key] += int(result.get(key, 0))
    print(json.dumps({"input_rows": len(raw), "accepted_rows": len(facilities), **totals}, indent=2))


if __name__ == "__main__":
    main()
