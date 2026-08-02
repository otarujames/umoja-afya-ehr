from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Facility
from ..schemas import FacilityOut

router = APIRouter(tags=["Facilities"])


@router.get("/facilities", response_model=list[FacilityOut])
def list_facilities(country_code: str | None = Query(default=None, min_length=2, max_length=3), db: Session = Depends(get_db)):
    query = select(Facility).where(Facility.active.is_(True))
    if country_code:
        query = query.where(Facility.country_code == country_code.upper())
    return list(db.scalars(query.order_by(Facility.name)))
