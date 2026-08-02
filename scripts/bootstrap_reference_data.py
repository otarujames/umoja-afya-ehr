from __future__ import annotations

import sys
from pathlib import Path

import yaml
from sqlalchemy import select

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.database import SessionLocal  # noqa: E402
from backend.app.models import Facility  # noqa: E402
from backend.app.country_seed import FACILITIES as COUNTRY_FACILITIES  # noqa: E402


def relation_for(code: str) -> str:
    if code.startswith("MNH-"):
        return "Muhimbili National Hospital campus"
    if code in {"MOI", "JKCI", "ORCI"}:
        return "Connected autonomous specialist institution"
    return "Connected health facility"


def main() -> None:
    source = ROOT / "config" / "facilities.yml"
    data = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
    records = data.get("facilities", [])
    if not records:
        raise SystemExit("No facilities are defined in config/facilities.yml")

    created = updated = 0
    with SessionLocal() as db:
        for record in records:
            code = str(record["code"]).strip().upper()
            item = db.scalar(select(Facility).where(Facility.code == code))
            if not item:
                item = Facility(
                    code=code,
                    name=record["name"],
                    facility_type=record.get("type", "health_facility"),
                    relation=record.get("relation", relation_for(code)),
                    active=True,
                )
                db.add(item)
                created += 1
            else:
                item.name = record["name"]
                item.facility_type = record.get("type", item.facility_type)
                item.relation = record.get("relation", relation_for(code))
                item.active = True
                updated += 1
        for country_code, country_rows in COUNTRY_FACILITIES.items():
            for code, name, facility_type, region, ownership in country_rows:
                item = db.scalar(select(Facility).where(Facility.code == code))
                if not item:
                    db.add(Facility(code=code, name=name, facility_type=facility_type, relation=f"{country_code} practice context", active=True, region=region, council=region, ownership_category=ownership, source_system="Configured multi-country directory", country_code=country_code))
                    created += 1
                else:
                    item.name=name; item.facility_type=facility_type; item.region=region; item.council=region; item.ownership_category=ownership; item.country_code=country_code; item.active=True
                    updated += 1
        db.commit()
    print(f"Reference multi-country facility registry synchronized: {created} created, {updated} updated.")


if __name__ == "__main__":
    main()
