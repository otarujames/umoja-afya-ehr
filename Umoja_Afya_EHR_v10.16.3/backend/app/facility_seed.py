from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Facility

# Public facilities verifiable from Tanzania Ministry of Health HFR public category pages.
# The national HFR master facility list requires a formal Ministry request; the application
# therefore supports later authoritative HFR import without overwriting local configuration.
PUBLIC_HOSPITALS = [
    # National and national super-specialized
    dict(code="MNH-UPANGA", hfr_code="105651-4", name="Muhimbili National Hospital — Upanga", facility_type="National Hospital", region="Dar es Salaam Region", council="Ilala MC", ownership_authority="MoH", hierarchy_level="NATIONAL", relation="National referral and teaching hospital"),
    dict(code="MNH-MLOGANZILA", hfr_code="111890-0", name="Muhimbili National Hospital — Mloganzila", facility_type="National Super Specialized Hospital", region="Dar es Salaam Region", council="Ubungo MC", ownership_authority="MoH", hierarchy_level="NATIONAL_SPECIALIZED", parent_code="MNH-UPANGA", relation="MNH campus"),
    dict(code="JKCI", hfr_code="111836-3", name="Jakaya Kikwete Cardiac Institute", facility_type="National Super Specialized Hospital", region="Dar es Salaam Region", council="Ilala MC", ownership_authority="MoH", hierarchy_level="NATIONAL_SPECIALIZED", relation="Cardiovascular specialty institute"),
    dict(code="KIDH", hfr_code="110886-9", name="Kibong'oto Infectious Diseases Hospital", facility_type="National Super Specialized Hospital", region="Kilimanjaro Region", council="Siha DC", ownership_authority="MoH", hierarchy_level="NATIONAL_SPECIALIZED", relation="Infectious diseases specialty hospital"),
    dict(code="ORCI", hfr_code="106880-8", name="Ocean Road Cancer Institute", facility_type="National Super Specialized Hospital", region="Dar es Salaam Region", council="Ilala MC", ownership_authority="MoH", hierarchy_level="NATIONAL_SPECIALIZED", relation="National cancer institute"),
    dict(code="MOI", hfr_code="105267-9", name="Muhimbili Orthopaedic Institute", facility_type="National Super Specialized Hospital", region="Dar es Salaam Region", council="Ilala MC", ownership_authority="MoH", hierarchy_level="NATIONAL_SPECIALIZED", relation="Orthopaedics, trauma and neurosurgery institute"),
    dict(code="MIREMBE", hfr_code="104962-6", name="Mirembe National Mental Health Hospital", facility_type="National Super Specialized Hospital", region="Dodoma Region", council="Dodoma CC", ownership_authority="MoH", hierarchy_level="NATIONAL_SPECIALIZED", relation="National mental health hospital"),
    # Zonal referral hospitals
    dict(code="ZR-MTWARA", hfr_code="120486-6", name="Mtwara Southern Zone Referral Hospital", facility_type="Zonal Referral Hospital", region="Mtwara Region", council="Mtwara MC", ownership_authority="MoH", hierarchy_level="ZONAL", relation="Southern zone referral"),
    dict(code="ZR-CHATO", hfr_code="120343-9", name="Chato Zonal Referral Hospital", facility_type="Zonal Referral Hospital", region="Geita Region", council="Chato DC", ownership_authority="MoH", hierarchy_level="ZONAL", relation="Lake zone referral"),
    dict(code="BMH", hfr_code="111841-3", name="Benjamin Mkapa Hospital", facility_type="Zonal Referral Hospital", region="Dodoma Region", council="Dodoma CC", ownership_authority="MoH", hierarchy_level="ZONAL", relation="Central zone referral"),
    dict(code="MZRH", hfr_code="104601-0", name="Mbeya Zonal Referral Hospital", facility_type="Zonal Referral Hospital", region="Mbeya Region", council="Mbeya CC", ownership_authority="MoH", hierarchy_level="ZONAL", relation="Southern highlands zone referral"),
    dict(code="LUGALO", hfr_code="103632-6", name="Lugalo Zonal Referral Hospital", facility_type="Zonal Referral Hospital", region="Dar es Salaam Region", council="Kinondoni MC", ownership_authority="Military", hierarchy_level="ZONAL", relation="Military zonal referral hospital"),
    # Regional referral hospitals (28 official public HFR records)
    dict(code="RRH-AMANA", hfr_code="100097-5", name="Amana Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Dar es Salaam Region", council="Ilala MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-TANGA", hfr_code="100405-0", name="Tanga Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Tanga Region", council="Tanga CC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-DODOMA", hfr_code="100991-9", name="Dodoma Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Dodoma Region", council="Dodoma CC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-GEITA", hfr_code="101192-3", name="Geita Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Geita Region", council="Geita TC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-IRINGA", hfr_code="101854-8", name="Iringa Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Iringa Region", council="Iringa MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-BUKOBA", hfr_code="102162-5", name="Bukoba Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Kagera Region", council="Bukoba MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-LIGULA", hfr_code="103503-9", name="Ligula Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Mtwara Region", council="Mtwara MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-MANYARA", hfr_code="104279-5", name="Manyara Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Manyara Region", council="Babati TC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-MAWENZI", hfr_code="104514-5", name="Mawenzi Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Kilimanjaro Region", council="Moshi MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-MBEYA", hfr_code="104602-8", name="Mbeya Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Mbeya Region", council="Mbeya CC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-MOROGORO", hfr_code="105299-2", name="Morogoro Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Morogoro Region", council="Morogoro MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-MT-MERU", hfr_code="105316-4", name="Mount Meru Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Arusha Region", council="Arusha CC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-MUSOMA", hfr_code="105721-5", name="Mwalimu Nyerere Memorial Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Mara Region", council="Musoma MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-MWANANYAMALA", hfr_code="105905-4", name="Mwananyamala Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Dar es Salaam Region", council="Kinondoni MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-SEKOU-TOURE", hfr_code="107354-3", name="Sekou-Toure Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Mwanza Region", council="Nyamagana MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-SHINYANGA", hfr_code="107423-6", name="Shinyanga Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Shinyanga Region", council="Shinyanga MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-SINGIDA", hfr_code="107485-5", name="Singida Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Singida Region", council="Singida MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-SOKOINE", hfr_code="107517-5", name="Sokoine Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Lindi Region", council="Lindi MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-RUVUMA", hfr_code="107543-1", name="Ruvuma Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Ruvuma Region", council="Songea MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-SUMBAWANGA", hfr_code="107663-7", name="Sumbawanga Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Rukwa Region", council="Sumbawanga MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-KITETE", hfr_code="107703-1", name="Kitete Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Tabora Region", council="Tabora MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-TEMEKE", hfr_code="107806-2", name="Temeke Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Dar es Salaam Region", council="Temeke MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-TUMBI", hfr_code="107942-5", name="Tumbi Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Pwani Region", council="Kibaha TC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-MAWENI", hfr_code="108713-9", name="Maweni Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Kigoma Region", council="Kigoma Ujiji MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-NJOMBE", hfr_code="113689-4", name="Njombe Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Njombe Region", council="Njombe TC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-SIMIYU", hfr_code="113724-9", name="Simiyu Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Simiyu Region", council="Bariadi TC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-SONGWE", hfr_code="120626-7", name="Songwe Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Songwe Region", council="Mbozi DC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    dict(code="RRH-KATAVI", hfr_code="121927-8", name="Katavi Regional Referral Hospital", facility_type="Regional Referral Hospital", region="Katavi Region", council="Mpanda MC", ownership_authority="MoH", hierarchy_level="REGIONAL", relation="Regional referral hospital"),
    # Zanzibar government-hospital contexts, included for rollout configuration; authoritative Zanzibar registry sync remains separate.
    dict(code="ZNZ-MNAZI-MMOJA", hfr_code=None, name="Mnazi Mmoja Hospital", facility_type="National Referral Hospital", region="Mjini Magharibi", council="Urban West", ownership_authority="Zanzibar Ministry of Health", hierarchy_level="ZANZIBAR_NATIONAL", relation="Zanzibar national referral context"),
    dict(code="ZNZ-ABDALLA-MZEE", hfr_code=None, name="Abdalla Mzee Hospital", facility_type="Regional Hospital", region="Kusini Pemba", council="Mkoani", ownership_authority="Zanzibar Ministry of Health", hierarchy_level="ZANZIBAR_REGIONAL", relation="Pemba referral context"),
    dict(code="ZNZ-KIVUNGE", hfr_code=None, name="Kivunge Hospital", facility_type="District/Regional Hospital", region="Kaskazini Unguja", council="Kaskazini A", ownership_authority="Zanzibar Ministry of Health", hierarchy_level="ZANZIBAR_DISTRICT", relation="Zanzibar government hospital context"),
    dict(code="ZNZ-MAKUNDUCHI", hfr_code=None, name="Makunduchi Hospital", facility_type="District Hospital", region="Kusini Unguja", council="Kusini", ownership_authority="Zanzibar Ministry of Health", hierarchy_level="ZANZIBAR_DISTRICT", relation="Zanzibar government hospital context"),
]


def seed_public_facilities(db: Session) -> int:
    count = 0
    for row in PUBLIC_HOSPITALS:
        item = db.scalar(select(Facility).where(Facility.code == row["code"]))
        if not item:
            item = Facility(code=row["code"], name=row["name"], facility_type=row["facility_type"], relation=row["relation"])
            db.add(item)
            db.flush()
            count += 1
        for field in ("hfr_code", "name", "facility_type", "region", "council", "ownership_authority", "hierarchy_level", "parent_code", "relation"):
            if field in row:
                setattr(item, field, row.get(field))
        item.ownership_category = "Public"
        item.source_system = "Tanzania HFR public portal" if row.get("hfr_code") else "Configured Zanzibar rollout context"
        item.active = True
    db.commit()
    return count
