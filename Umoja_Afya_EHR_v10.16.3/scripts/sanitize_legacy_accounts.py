#!/usr/bin/env python3
"""Disable legacy demonstration accounts from older releases without touching real users."""
from pathlib import Path
import sys
from sqlalchemy import select
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app.database import SessionLocal
from backend.app.enterprise_models import UserAccount
from backend.app.operational_models import UserSession

LEGACY_SIGNATURES={
    "doctor":("Dr. Neema M.","physician"),
    "nurse":("Neema Kweka, RN","nurse"),
    "registration":("Amina Salum","registration"),
    "pharmacy":("Pharm. Juma K.","pharmacy"),
    "laboratory":("Grace Mushi","laboratory"),
    "operations":("Dr. Rahma L.","operations"),
    "finance":("Hassan Bakari","finance"),
    "admin":("ICT Administrator","admin"),
}

def main():
    disabled=[]
    with SessionLocal() as db:
        for username,(display,role) in LEGACY_SIGNATURES.items():
            user=db.scalar(select(UserAccount).where(UserAccount.username==username,UserAccount.display_name==display,UserAccount.role_code==role))
            if not user: continue
            user.active=False
            user.must_change_password=True
            for session in db.scalars(select(UserSession).where(UserSession.user_account_id==user.id)).all():
                session.revoked_at=session.revoked_at or session.expires_at
            disabled.append(username)
        db.commit()
    print("Legacy demonstration accounts disabled: "+(", ".join(disabled) if disabled else "none found"))
if __name__=='__main__': main()
