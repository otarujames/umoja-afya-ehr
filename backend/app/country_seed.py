from datetime import date, datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import Facility, Patient

FACILITIES={
"KE":[("KE-KNH","Kenyatta National Hospital","National Referral Hospital","Nairobi","Public"),("KE-MTRH","Moi Teaching and Referral Hospital","National Referral Hospital","Uasin Gishu","Public"),("KE-KUTRRH","Kenyatta University Teaching, Referral & Research Hospital","National Referral Hospital","Nairobi","Public"),("KE-NSIRH","National Spinal Injury and Referral Hospital","Specialized Hospital","Nairobi","Public"),("KE-AKUH","Aga Khan University Hospital Nairobi","Private Teaching Hospital","Nairobi","Private"),("KE-NAIROBI-HOSP","The Nairobi Hospital","Private Hospital","Nairobi","Private"),("KE-MPSHAH","M.P. Shah Hospital","Private Hospital","Nairobi","Private"),("KE-AAR","AAR Hospital Nairobi","Private Hospital","Nairobi","Private"),("KE-KIJABE","AIC Kijabe Hospital","Faith-Based Hospital","Kiambu","Faith-Based"),("KE-NAKURU-L6","Nakuru Level 6 Hospital","County Referral Hospital","Nakuru","Public"),("KE-TENWEK","Tenwek Hospital","Faith-Based Hospital","Bomet","Faith-Based"),("KE-MOMBASA-HOSP","The Mombasa Hospital","Private Hospital","Mombasa","Private")],
"NG":[("NG-NHA","National Hospital Abuja","Federal Tertiary Hospital","FCT Abuja","Public"),("NG-UATH","University of Abuja Teaching Hospital","Federal Teaching Hospital","FCT Abuja","Public"),("NG-CEDARCREST","Cedarcrest Hospitals","Private Specialty Hospital","FCT Abuja","Private"),("NG-NISA","Nisa Premier Hospital","Private Specialist Hospital","FCT Abuja","Private"),("NG-JUTH","Jos University Teaching Hospital","Federal Teaching Hospital","Plateau","Public"),("NG-UITH","University of Ilorin Teaching Hospital","Federal Teaching Hospital","Kwara","Public"),("NG-AKTH","Aminu Kano Teaching Hospital","Federal Teaching Hospital","Kano","Public"),("NG-ABUTH","Ahmadu Bello University Teaching Hospital","Federal Teaching Hospital","Kaduna","Public"),("NG-UDUTH","Usmanu Danfodiyo University Teaching Hospital","Federal Teaching Hospital","Sokoto","Public"),("NG-UMTH","University of Maiduguri Teaching Hospital","Federal Teaching Hospital","Borno","Public"),("NG-ATBUTH","Abubakar Tafawa Balewa University Teaching Hospital","Federal Teaching Hospital","Bauchi","Public"),("NG-LUTH","Lagos University Teaching Hospital","Federal Teaching Hospital","Lagos","Public"),("NG-LASUTH","Lagos State University Teaching Hospital","State Teaching Hospital","Lagos","Public"),("NG-UCH","University College Hospital Ibadan","Federal Teaching Hospital","Oyo","Public"),("NG-UNTH","University of Nigeria Teaching Hospital","Federal Teaching Hospital","Enugu","Public"),("NG-NAUTH","Nnamdi Azikiwe University Teaching Hospital","Federal Teaching Hospital","Anambra","Public"),("NG-UBTH","University of Benin Teaching Hospital","Federal Teaching Hospital","Edo","Public"),("NG-ISTH","Irrua Specialist Teaching Hospital","Federal Specialist Hospital","Edo","Public"),("NG-UPTH","University of Port Harcourt Teaching Hospital","Federal Teaching Hospital","Rivers","Public"),("NG-MERIDIAN","Meridian Hospitals","Private Hospital","Rivers","Private")]}
NAMES={"KE":(["Akinyi","Wanjiku","Njeri","Amina","Atieno","Chebet","Wambui","Zawadi","Faith","Mercy","Brian","Kevin","Kamau","Otieno","Kiptoo","Mwangi"],["Omondi","Kamau","Wanjala","Kiptoo","Mutiso","Njoroge","Odhiambo","Maina","Kariuki","Mwangi"]),"NG":(["Chinedu","Ngozi","Amina","Musa","Ifeoma","Emeka","Bola","Tunde","Yemi","Adaeze","Fatima","Sani","Blessing","David","Chioma","Ibrahim"],["Okafor","Adebayo","Mohammed","Eze","Balogun","Abubakar","Nwosu","Ogunleye","Bello","Umar"])}
def seed_country_contexts(db:Session, per_country:int=500):
    for cc, rows in FACILITIES.items():
        for code,name,ftype,region,owner in rows:
            item=db.scalar(select(Facility).where(Facility.code==code))
            if not item:
                item=Facility(code=code,name=name,facility_type=ftype,relation=f"{cc} practice context",region=region,council=region,ownership_category=owner,source_system="Configured multi-country directory",country_code=cc)
                db.add(item)
            else:item.country_code=cc
    for cc,(firsts,lasts) in NAMES.items():
        current=len(list(db.scalars(select(Patient.id).where(Patient.country_code==cc)).all()))
        for i in range(current+1,per_country+1):
            prefix="KE" if cc=="KE" else "NG"; phone="+254 7" if cc=="KE" else "+234 80"
            db.add(Patient(mpi_id=f"{prefix}-MPI-{i:08d}",mrn=f"{prefix}-{i:08d}",first_name=firsts[(i-1)%len(firsts)],last_name=lasts[(i*3)%len(lasts)],date_of_birth=date(1950+(i%65),1+(i%12),1+(i%27)),sex="Female" if i%2==0 else "Male",phone=f"{phone}{1000000+i:07d}",address=("Nairobi, Kenya" if cc=="KE" else "Abuja, Nigeria"),region=("Nairobi" if cc=="KE" else "FCT Abuja"),district=("Nairobi" if cc=="KE" else "Abuja Municipal"),payer=("SHA" if cc=="KE" else "NHIA"),member_number=f"{prefix}-MEM-{i:07d}",country_code=cc,created_at=datetime.now(timezone.utc)))
    db.commit()

MULTICULTURAL_NAMES = {
    "TZ": {
        "first": ["Asha", "Baraka", "Neema", "Juma", "Zawadi", "Rehema", "Hamisi", "Mariam", "Tumaini", "Salim", "Pendo", "Yohana"],
        "last": ["Mwakalinga", "Msuya", "Mhando", "Kweka", "Mushi", "Mrema", "Mashauri", "Komba", "Mwakyusa", "Mfinanga", "Nyerere", "Shayo"],
        "cities": [("Dar es Salaam", "Kinondoni"), ("Arusha", "Arusha"), ("Mwanza", "Nyamagana"), ("Dodoma", "Dodoma"), ("Kilimanjaro", "Moshi")],
        "payer": ["NHIF", "iCHF", "UHI", "Cash"], "phone": "+255 7"
    },
    "KE": {
        "first": ["Akinyi", "Wanjiku", "Njeri", "Atieno", "Chebet", "Wambui", "Kamau", "Otieno", "Kiptoo", "Mwangi", "Amina", "Zawadi"],
        "last": ["Omondi", "Kamau", "Wanjala", "Kiptoo", "Mutiso", "Njoroge", "Odhiambo", "Maina", "Kariuki", "Mwangi", "Wekesa", "Cheruiyot"],
        "cities": [("Nairobi", "Nairobi"), ("Uasin Gishu", "Eldoret"), ("Mombasa", "Mombasa"), ("Nakuru", "Nakuru"), ("Kisumu", "Kisumu")],
        "payer": ["SHA", "Private", "Cash", "Employer"], "phone": "+254 7"
    },
    "NG": {
        "first": ["Chinedu", "Ngozi", "Amina", "Musa", "Ifeoma", "Emeka", "Bola", "Tunde", "Yemi", "Adaeze", "Fatima", "Sani", "Chioma", "Ibrahim"],
        "last": ["Okafor", "Adebayo", "Mohammed", "Eze", "Balogun", "Abubakar", "Nwosu", "Ogunleye", "Bello", "Umar", "Adeyemi", "Obi"],
        "cities": [("FCT Abuja", "Abuja Municipal"), ("Lagos", "Ikeja"), ("Kano", "Kano Municipal"), ("Enugu", "Enugu North"), ("Rivers", "Port Harcourt")],
        "payer": ["NHIA", "HMO", "Private", "Cash"], "phone": "+234 80"
    },
    "UG": {
        "first": ["Achen", "Akello", "Atim", "Nabirye", "Nakato", "Namusoke", "Kato", "Okello", "Ssemanda", "Tumusiime", "Mugisha", "Auma"],
        "last": ["Ochieng", "Kato", "Nsubuga", "Nabwire", "Okot", "Ssentongo", "Tumwesigye", "Akena", "Byaruhanga", "Namusoke", "Kisembo", "Wanyama"],
        "cities": [("Kampala", "Central"), ("Wakiso", "Wakiso"), ("Gulu", "Gulu City"), ("Mbarara", "Mbarara City")],
        "payer": ["Private", "Employer", "Cash"], "phone": "+256 7"
    },
    "ZA": {
        "first": ["Thandiwe", "Noluthando", "Lerato", "Ayanda", "Zanele", "Sipho", "Thabo", "Kagiso", "Lwazi", "Bongani", "Nomsa", "Siyabonga"],
        "last": ["Dlamini", "Nkosi", "Mthembu", "Khumalo", "Ndlovu", "Mokoena", "Mahlangu", "Mabena", "Zulu", "Maseko", "Molefe", "Sithole"],
        "cities": [("Gauteng", "Johannesburg"), ("Western Cape", "Cape Town"), ("KwaZulu-Natal", "Durban"), ("Eastern Cape", "Gqeberha")],
        "payer": ["Medical Aid", "Private", "Cash"], "phone": "+27 7"
    },
}


def seed_multicultural_patients(db: Session, target_total: int = 15000) -> None:
    """Add culturally varied synthetic patients without altering production records.

    Uganda and South Africa are represented as cross-border residents/visitors in the
    three enabled practice countries. This preserves country-context isolation while
    ensuring realistic regional name diversity for training and review.
    """
    current = int(db.scalar(select(__import__('sqlalchemy').func.count(Patient.id))) or 0)
    if current >= target_total:
        return
    cultures = ["TZ", "KE", "NG", "UG", "ZA"]
    context_cycle = {"TZ": ["TZ"], "KE": ["KE"], "NG": ["NG"], "UG": ["TZ", "KE"], "ZA": ["TZ", "KE", "NG"]}
    additions = target_total - current
    for offset in range(additions):
        culture = cultures[offset % len(cultures)]
        profile = MULTICULTURAL_NAMES[culture]
        seq = current + offset + 1
        context = context_cycle[culture][offset % len(context_cycle[culture])]
        first = profile["first"][offset % len(profile["first"])]
        last = profile["last"][(offset * 5 + 3) % len(profile["last"])]
        region, district = profile["cities"][(offset * 3) % len(profile["cities"])]
        prefix = f"{context}-{culture}"
        db.add(Patient(
            mpi_id=f"{prefix}-MPI-{seq:08d}", mrn=f"{prefix}-{seq:08d}",
            first_name=first, middle_name=None, last_name=last,
            date_of_birth=date(1942 + (offset % 78), 1 + (offset % 12), 1 + (offset % 27)),
            sex="Female" if offset % 2 == 0 else "Male",
            phone=f"{profile['phone']}{(1000000 + seq) % 90000000:07d}",
            address=f"{district}, {region} · {culture} heritage",
            region=region, district=district,
            payer=profile["payer"][offset % len(profile["payer"])],
            member_number=f"{prefix}-MEM-{seq:07d}",
            allergies="No known drug allergies", problems="Not yet assessed",
            medications="Medication reconciliation pending", consent_status="OBTAINED",
            identity_status="SYNTHETIC_VERIFIED", country_code=context,
            created_at=datetime.now(timezone.utc)
        ))
        if offset and offset % 750 == 0:
            db.flush()
    db.commit()
