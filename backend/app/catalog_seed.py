from __future__ import annotations

import json
import re
from itertools import product

from sqlalchemy import select
from sqlalchemy.orm import Session

from .enhancement_models import OrderCatalogItem, OrderSet, OrderSetItem


def _code(category: str, name: str) -> str:
    slug = re.sub(r"[^A-Z0-9]+", "-", name.upper()).strip("-")[:72]
    return f"{category[:10].upper()}-{slug}"


def _add(rows: list[dict], category: str, names: list[str], *, clinical: bool = True, department: str | None = None,
         subcategory: str | None = None, specimen: str | None = None, priority: str = "ROUTINE",
         instructions: str | None = None, synonyms: str | None = None, route: str | None = None,
         requires_reason: bool = False, requires_cosign: bool = False) -> None:
    for name in names:
        rows.append({
            "orderable_code": _code(category, name),
            "display_name": name,
            "category": category,
            "subcategory": subcategory,
            "clinical": clinical,
            "department": department,
            "specimen": specimen,
            "default_priority": priority,
            "default_instructions": instructions,
            "synonyms": synonyms,
            "route": route,
            "requires_reason": requires_reason,
            "requires_cosign": requires_cosign,
            "active": True,
            "metadata_json": json.dumps({"source": "Umoja Afya national starter catalog", "configurable": True}),
        })


def build_order_catalog() -> list[dict]:
    rows: list[dict] = []

    _add(
        rows,
        "ADT",
        ["Admit to inpatient service"],
        department="Registration / ADT",
        subcategory="Admission",
        instructions="Select the destination service, level of care and requested bed or unit.",
        synonyms="admit admission inpatient bed request hospitalize",
        requires_reason=True,
    )

    _add(rows, "LABORATORY", [
        "Complete blood count", "Full blood picture", "Haemoglobin and haematocrit", "White blood cell differential",
        "Platelet count", "Reticulocyte count", "Peripheral blood film", "Erythrocyte sedimentation rate",
        "Sickle cell screen", "Haemoglobin electrophoresis", "Malaria rapid diagnostic test", "Malaria blood film",
        "Blood group and Rh typing", "Direct antiglobulin test", "Indirect antiglobulin test",
        "Prothrombin time and INR", "Activated partial thromboplastin time", "Fibrinogen", "D-dimer",
        "Bleeding time", "Clotting time", "Factor VIII assay", "Factor IX assay",
    ], department="Laboratory", subcategory="Hematology", specimen="Whole blood")

    _add(rows, "LABORATORY", [
        "Basic metabolic panel", "Comprehensive metabolic panel", "Urea and electrolytes", "Renal function panel",
        "Liver function panel", "Cardiac enzyme panel", "Lipid profile", "Bone profile", "Iron studies",
        "Serum sodium", "Serum potassium", "Serum chloride", "Serum bicarbonate", "Serum urea",
        "Serum creatinine", "Estimated GFR", "Serum glucose", "Random blood glucose", "Fasting blood glucose",
        "Oral glucose tolerance test", "HbA1c", "Serum calcium", "Ionized calcium", "Serum magnesium",
        "Serum phosphate", "Serum uric acid", "Total protein", "Serum albumin", "Total bilirubin",
        "Direct bilirubin", "ALT", "AST", "ALP", "GGT", "LDH", "Amylase", "Lipase", "Creatine kinase",
        "CK-MB", "High sensitivity troponin I", "High sensitivity troponin T", "NT-proBNP", "Serum lactate",
        "C-reactive protein", "Procalcitonin", "Serum osmolality", "Serum ethanol", "Acetaminophen level",
        "Salicylate level", "Therapeutic drug level - digoxin", "Therapeutic drug level - vancomycin",
        "Therapeutic drug level - gentamicin", "Therapeutic drug level - phenytoin", "Therapeutic drug level - valproate",
    ], department="Laboratory", subcategory="Chemistry", specimen="Serum or plasma")

    _add(rows, "LABORATORY", [
        "Urinalysis", "Urine microscopy", "Urine protein", "Urine protein/creatinine ratio", "Urine albumin/creatinine ratio",
        "24-hour urine protein", "Urine electrolytes", "Urine pregnancy test", "Urine toxicology screen",
        "Stool microscopy", "Stool occult blood", "Stool culture", "Stool ova and parasites", "Faecal calprotectin",
        "Cerebrospinal fluid analysis", "Pleural fluid analysis", "Ascitic fluid analysis", "Synovial fluid analysis",
    ], department="Laboratory", subcategory="Urine and body fluids")

    _add(rows, "LABORATORY", [
        "Blood culture - aerobic", "Blood culture - anaerobic", "Urine culture and sensitivity", "Sputum culture and sensitivity",
        "Wound swab culture", "High vaginal swab culture", "Cervical swab culture", "Urethral swab culture",
        "CSF culture", "Stool culture", "MRSA screen", "VRE screen", "Carbapenemase screen", "Gram stain",
        "AFB smear", "Mycobacterial culture", "GeneXpert MTB/RIF", "TB LAM", "Fungal microscopy and culture",
        "Cryptococcal antigen", "H. pylori stool antigen", "H. pylori breath test", "COVID-19 antigen test",
        "SARS-CoV-2 PCR", "Influenza A/B PCR", "RSV PCR", "Respiratory viral panel", "Meningitis/encephalitis PCR panel",
        "Gastrointestinal pathogen PCR panel", "Gonorrhoea NAAT", "Chlamydia NAAT", "Trichomonas NAAT",
    ], department="Laboratory", subcategory="Microbiology")

    _add(rows, "LABORATORY", [
        "HIV rapid test", "HIV antigen/antibody test", "HIV viral load", "CD4 count", "Hepatitis B surface antigen",
        "Hepatitis B surface antibody", "Hepatitis B core antibody", "Hepatitis C antibody", "Hepatitis C viral load",
        "Syphilis RPR", "Syphilis TPHA", "Toxoplasma IgG/IgM", "Rubella IgG", "CMV IgG/IgM", "Dengue antigen/antibody",
        "Brucella serology", "ANA", "Anti-dsDNA", "Rheumatoid factor", "Anti-CCP", "Complement C3", "Complement C4",
        "Thyroid stimulating hormone", "Free T4", "Free T3", "Cortisol", "ACTH", "Prolactin", "FSH", "LH",
        "Estradiol", "Progesterone", "Testosterone", "Beta-hCG quantitative", "PSA", "AFP", "CEA", "CA-125",
        "CA 19-9", "CA 15-3", "Calcitonin", "PTH", "Vitamin D", "Vitamin B12", "Folate",
    ], department="Laboratory", subcategory="Immunology and endocrinology", specimen="Serum")

    _add(rows, "LABORATORY", [
        "Surgical pathology - small specimen", "Surgical pathology - large specimen", "Frozen section",
        "Cytology - cervical smear", "Fine needle aspiration cytology", "Bone marrow aspirate", "Bone marrow trephine biopsy",
        "Immunohistochemistry panel", "HER2 testing", "ER/PR receptor testing", "Ki-67 index", "Flow cytometry",
        "Molecular tumour panel", "BRCA1/BRCA2 testing", "EGFR mutation testing", "ALK rearrangement testing",
    ], department="Pathology", subcategory="Anatomic pathology", requires_reason=True)

    _add(rows, "BLOOD_BANK", [
        "Type and screen", "Group and save", "Crossmatch packed red blood cells", "Prepare packed red blood cells",
        "Prepare fresh frozen plasma", "Prepare platelets", "Prepare cryoprecipitate", "Prepare whole blood",
        "Emergency release blood", "Massive transfusion protocol", "Neonatal exchange transfusion preparation",
        "Irradiated blood products", "Leukoreduced blood products", "Washed red blood cells",
    ], department="Blood Bank", subcategory="Transfusion", requires_reason=True)

    xray_parts = ["Chest", "Abdomen", "Pelvis", "Cervical spine", "Thoracic spine", "Lumbar spine", "Skull", "Facial bones",
                  "Shoulder", "Humerus", "Elbow", "Forearm", "Wrist", "Hand", "Finger", "Hip", "Femur", "Knee",
                  "Tibia/fibula", "Ankle", "Foot", "Toe"]
    _add(rows, "IMAGING", [f"X-ray {part} - standard views" for part in xray_parts] +
         ["Portable chest X-ray", "Skeletal survey", "Bone age study", "Dental panoramic X-ray"],
         department="Radiology", subcategory="Radiography", requires_reason=True)

    _add(rows, "IMAGING", [
        "CT head without contrast", "CT head with contrast", "CT angiography head and neck", "CT cervical spine",
        "CT chest without contrast", "CT chest with contrast", "CT pulmonary angiography", "CT abdomen and pelvis without contrast",
        "CT abdomen and pelvis with contrast", "CT renal stone protocol", "CT trauma whole body", "CT aortogram",
        "CT coronary angiography", "CT temporal bones", "CT sinuses", "CT facial bones", "CT lower limb angiography",
        "CT upper limb angiography", "CT colonography", "CT-guided biopsy", "CT-guided drainage",
    ], department="Radiology", subcategory="CT", requires_reason=True)

    _add(rows, "IMAGING", [
        "MRI brain", "MRI brain with contrast", "MR angiography brain", "MR venography brain", "MRI pituitary",
        "MRI cervical spine", "MRI thoracic spine", "MRI lumbar spine", "MRI whole spine", "MRI shoulder", "MRI elbow",
        "MRI wrist", "MRI hand", "MRI hip", "MRI knee", "MRI ankle", "MRI foot", "MRI abdomen", "MRCP",
        "MRI pelvis", "MRI prostate", "MRI breast", "MRI cardiac", "MRI fetal", "MRI enterography",
    ], department="Radiology", subcategory="MRI", requires_reason=True)

    _add(rows, "IMAGING", [
        "Ultrasound abdomen", "Ultrasound pelvis", "Ultrasound renal tract", "Ultrasound thyroid", "Ultrasound scrotum",
        "Ultrasound soft tissue", "Ultrasound breast", "Ultrasound neonatal head", "Obstetric ultrasound - dating",
        "Obstetric ultrasound - anomaly scan", "Obstetric ultrasound - growth and wellbeing", "Biophysical profile",
        "Transvaginal ultrasound", "Carotid Doppler ultrasound", "Upper limb venous Doppler", "Lower limb venous Doppler",
        "Upper limb arterial Doppler", "Lower limb arterial Doppler", "Portal vein Doppler", "Ultrasound-guided biopsy",
        "Ultrasound-guided aspiration", "FAST trauma ultrasound",
    ], department="Radiology", subcategory="Ultrasound", requires_reason=True)

    _add(rows, "CARDIOLOGY", [
        "12-lead ECG", "Rhythm strip", "24-hour Holter monitor", "48-hour Holter monitor", "7-day event monitor",
        "Ambulatory blood pressure monitoring", "Transthoracic echocardiogram", "Transoesophageal echocardiogram",
        "Stress echocardiogram", "Exercise treadmill test", "Dobutamine stress test", "Cardiac catheterization",
        "Coronary angiography", "Right heart catheterization", "Pacemaker interrogation", "ICD interrogation",
        "Electrophysiology study", "Cardioversion", "Tilt table test",
    ], department="Cardiology", subcategory="Cardiac diagnostics", requires_reason=True)

    _add(rows, "PROCEDURE", [
        "Lumbar puncture", "Arterial line insertion", "Central venous catheter insertion", "PICC line insertion",
        "Peripheral IV cannulation", "Intraosseous access", "Chest tube insertion", "Thoracentesis", "Paracentesis",
        "Joint aspiration", "Bone marrow biopsy", "Liver biopsy", "Renal biopsy", "Skin biopsy", "Wound debridement",
        "Incision and drainage", "Suture repair", "Cast application", "Splint application", "Closed fracture reduction",
        "Nasogastric tube insertion", "Urinary catheterization", "Suprapubic catheterization", "Tracheostomy care",
        "Endotracheal intubation", "Mechanical ventilation initiation", "Non-invasive ventilation initiation",
        "Bronchoscopy", "Upper GI endoscopy", "Colonoscopy", "ERCP", "Cystoscopy", "Dialysis session",
        "Haemodialysis catheter insertion", "Peritoneal dialysis exchange", "Chemotherapy administration",
        "Radiotherapy treatment fraction", "Intrathecal medication administration", "Blood transfusion",
    ], department="Procedural Services", requires_reason=True)

    _add(rows, "CONSULT", [
        "General medicine consult", "General surgery consult", "Paediatrics consult", "Obstetrics and gynaecology consult",
        "Cardiology consult", "Neurology consult", "Neurosurgery consult", "Orthopaedics consult", "Trauma surgery consult",
        "Anaesthesia consult", "Critical care consult", "Nephrology consult", "Gastroenterology consult", "Hepatology consult",
        "Endocrinology consult", "Rheumatology consult", "Infectious diseases consult", "Pulmonology consult",
        "Haematology consult", "Medical oncology consult", "Radiation oncology consult", "Urology consult", "ENT consult",
        "Ophthalmology consult", "Dermatology consult", "Psychiatry consult", "Clinical psychology consult",
        "Dental/maxillofacial consult", "Physiotherapy consult", "Occupational therapy consult", "Speech therapy consult",
        "Nutrition and dietetics consult", "Palliative care consult", "Social work consult", "Pharmacy medication review",
        "Infection prevention consult", "Wound care consult", "Pain service consult", "Genetic counselling consult",
    ], department="Clinical Services", subcategory="Consultation", requires_reason=True)

    _add(rows, "NURSING", [
        "Vital signs monitoring", "Continuous pulse oximetry", "Cardiac telemetry", "Neurological observations",
        "Neurovascular observations", "Sepsis observations", "Early warning score monitoring", "Glucose monitoring",
        "Strict intake and output", "Daily weight", "Fluid restriction", "Fall precautions", "Pressure injury prevention",
        "Restraint monitoring", "Suicide precautions", "Seizure precautions", "Aspiration precautions", "Isolation precautions",
        "Contact precautions", "Droplet precautions", "Airborne precautions", "Wound care", "Stoma care", "Drain care",
        "Central line care", "Urinary catheter care", "Tracheostomy care", "Chest physiotherapy", "Oral care protocol",
        "Postoperative monitoring", "Post-transfusion monitoring", "Maternal observations", "Fetal heart monitoring",
        "Newborn observations", "Kangaroo mother care", "Breastfeeding support", "Pain assessment and reassessment",
    ], department="Nursing", subcategory="Nursing care")

    _add(rows, "RESPIRATORY", [
        "Oxygen via nasal cannula", "Oxygen via simple face mask", "Oxygen via non-rebreather mask", "High-flow nasal oxygen",
        "Nebulized bronchodilator", "Incentive spirometry", "Peak expiratory flow monitoring", "Arterial blood gas",
        "Venous blood gas", "Capillary blood gas", "Sputum induction", "Airway suction", "Ventilator protocol",
        "Spontaneous breathing trial", "Extubation readiness assessment", "CPAP therapy", "BiPAP therapy",
    ], department="Respiratory Therapy")

    _add(rows, "DIET", [
        "Regular diet", "Clear liquid diet", "Full liquid diet", "Soft diet", "Nil by mouth", "Diabetic diet",
        "Low sodium diet", "Renal diet", "Cardiac diet", "High protein diet", "Low residue diet", "Gluten-free diet",
        "Lactose-free diet", "Paediatric diet", "Pregnancy diet", "Enteral feeding protocol", "Tube feed formula",
        "Parenteral nutrition", "Fluid restriction 1000 mL/day", "Fluid restriction 1500 mL/day", "Oral nutrition supplements",
    ], department="Nutrition", clinical=True)

    _add(rows, "ACTIVITY", [
        "Activity as tolerated", "Bed rest", "Strict bed rest", "Bathroom privileges", "Ambulate with assistance",
        "Ambulate three times daily", "Weight bearing as tolerated", "Non-weight bearing", "Partial weight bearing",
        "Elevate affected limb", "Turn every 2 hours", "Progressive mobility protocol", "Spinal precautions",
        "Cervical collar at all times", "Hip precautions", "Sternal precautions",
    ], department="Clinical Care", clinical=True)

    common_meds = [
        "Paracetamol", "Ibuprofen", "Diclofenac", "Aspirin", "Morphine", "Tramadol", "Fentanyl", "Ketamine", "Lidocaine",
        "Amoxicillin", "Amoxicillin/clavulanate", "Penicillin V", "Benzylpenicillin", "Cloxacillin", "Ceftriaxone", "Cefotaxime",
        "Cefazolin", "Ceftazidime", "Cefepime", "Meropenem", "Piperacillin/tazobactam", "Vancomycin", "Gentamicin",
        "Amikacin", "Azithromycin", "Erythromycin", "Doxycycline", "Metronidazole", "Clindamycin", "Ciprofloxacin",
        "Levofloxacin", "Co-trimoxazole", "Fluconazole", "Amphotericin B", "Acyclovir", "Oseltamivir",
        "Isoniazid", "Rifampicin", "Pyrazinamide", "Ethambutol", "Dolutegravir/lamivudine/tenofovir",
        "Amlodipine", "Nifedipine", "Hydralazine", "Labetalol", "Losartan", "Enalapril", "Lisinopril", "Carvedilol",
        "Metoprolol", "Propranolol", "Furosemide", "Spironolactone", "Hydrochlorothiazide", "Atorvastatin", "Warfarin",
        "Heparin", "Enoxaparin", "Clopidogrel", "Alteplase", "Amiodarone", "Digoxin", "Adenosine", "Nitroglycerin",
        "Insulin regular", "Insulin NPH", "Insulin glargine", "Metformin", "Glibenclamide", "Dextrose 10%", "Dextrose 50%",
        "Normal saline", "Ringer's lactate", "Dextrose 5%", "Potassium chloride", "Magnesium sulfate", "Calcium gluconate",
        "Sodium bicarbonate", "Ondansetron", "Metoclopramide", "Omeprazole", "Pantoprazole", "Famotidine", "Lactulose",
        "Bisacodyl", "Loperamide", "Salbutamol", "Ipratropium", "Budesonide", "Prednisolone", "Dexamethasone",
        "Hydrocortisone", "Adrenaline", "Noradrenaline", "Dopamine", "Dobutamine", "Vasopressin", "Atropine",
        "Diazepam", "Midazolam", "Lorazepam", "Phenobarbital", "Phenytoin", "Levetiracetam", "Sodium valproate",
        "Haloperidol", "Olanzapine", "Fluoxetine", "Amitriptyline", "Oxytocin", "Misoprostol", "Ergometrine",
        "Tranexamic acid", "Ferrous sulfate", "Folic acid", "Vitamin K", "Vitamin A", "Zinc sulfate", "ORS",
        "Artemether/lumefantrine", "Artesunate", "Quinine", "Albendazole", "Praziquantel", "Permethrin",
    ]
    for route_name, route_code in [("oral", "PO"), ("intravenous", "IV"), ("intramuscular", "IM"), ("subcutaneous", "SC")]:
        # Route variants are valuable lookup orderables; not every drug is clinically valid for every route, so the catalog marks them configurable.
        names = [f"{med} - {route_name}" for med in common_meds]
        _add(rows, "MEDICATION", names, department="Pharmacy", subcategory="Medication", route=route_code,
             requires_reason=False, instructions="Dose, frequency, duration and indication must be completed at order entry.")

    _add(rows, "DISCHARGE", [
        "Discharge to home", "Discharge with clinic follow-up", "Discharge with home nursing", "Transfer to another hospital",
        "Transfer to rehabilitation facility", "Against medical advice discharge", "Palliative discharge", "Newborn discharge",
        "Generate discharge summary", "Medication reconciliation at discharge", "Patient education at discharge",
        "Follow-up appointment request", "Sick leave certificate", "Medical report request",
    ], department="Care Coordination", clinical=True, requires_reason=True)

    _add(rows, "REFERRAL", [
        "Internal referral", "Inter-facility referral", "Emergency transfer referral", "Specialist clinic referral",
        "Diagnostic referral", "Rehabilitation referral", "Mental health referral", "Social welfare referral",
        "Palliative care referral", "Community health worker follow-up", "District hospital referral", "Regional referral hospital referral",
        "Zonal referral hospital referral", "National hospital referral", "Cross-border referral",
    ], department="Referral Coordination", clinical=True, requires_reason=True)

    _add(rows, "TRANSPORT", [
        "Patient transport - wheelchair", "Patient transport - stretcher", "Patient transport - bed", "Patient transport - ambulance",
        "Return patient to unit", "Specimen collection transport", "Blood product transport", "Medication delivery",
        "Medical equipment transport", "Visitor pickup assistance", "Bariatric wheelchair request", "Oxygen cylinder delivery",
    ], department="Transport", clinical=False, subcategory="Patient and logistics transport")

    _add(rows, "EVS", [
        "Routine room cleaning", "Terminal room cleaning", "Isolation room terminal cleaning", "Bathroom cleaning",
        "Curtain replacement", "Curtain take down", "Curtain installation", "Spill cleanup", "Biohazard cleanup",
        "UV disinfection setup", "UV disinfection take down", "Bed space cleaning", "Theatre turnaround cleaning",
        "Waste collection", "Sharps container replacement", "Pest control request",
    ], department="Environmental Services", clinical=False)

    _add(rows, "EQUIPMENT", [
        "IV pole request", "Wheelchair request", "Stretcher request", "Oxygen concentrator request", "Oxygen cylinder request",
        "Portable suction request", "Infusion pump request", "Syringe pump request", "Patient monitor request",
        "Ventilator request", "CPAP machine request", "ECG machine request", "Defibrillator request", "Hospital bed request",
        "Pressure-relieving mattress request", "Bariatric bed request", "Incubator request", "Phototherapy unit request",
        "Portable ultrasound request", "Point-of-care glucose meter request", "Telemetry pack request", "Equipment repair request",
        "Preventive maintenance request", "Equipment decontamination request",
    ], department="Biomedical Engineering", clinical=False)

    _add(rows, "ADMINISTRATIVE", [
        "Interpreter request - Kiswahili", "Interpreter request - sign language", "Interpreter request - other language",
        "Patient identification reconciliation", "Duplicate patient merge review", "Medical records retrieval", "Chart deficiency review",
        "Consent form completion", "Insurance eligibility verification", "NHIF authorization request", "Private insurer authorization request",
        "Cash estimate request", "Deposit collection request", "Patient refund request", "Claim review request", "Claim resubmission request",
        "Coding review request", "Birth notification", "Death notification", "Mortuary transfer request", "Police notification",
        "Security assistance", "Patient property inventory", "Lost property request", "Complaint resolution request",
        "Patient relations consult", "Legal services review", "Occupational health review", "Staff incident report",
    ], department="Administration", clinical=False, requires_reason=True)

    # Deduplicate generated codes while preserving first definition.
    unique: dict[str, dict] = {}
    for row in rows:
        code = row["orderable_code"]
        if code in unique:
            suffix = 2
            while f"{code}-{suffix}" in unique:
                suffix += 1
            row["orderable_code"] = f"{code}-{suffix}"
        unique[row["orderable_code"]] = row
    return list(unique.values())


def _set_item(category: str, name: str, *, priority: str | None = None, indication: str | None = None,
              instructions: str | None = None, details: dict | None = None, required: bool = False) -> dict:
    return {
        "orderable_code": _code(category, name),
        "default_priority": priority,
        "default_indication": indication,
        "default_instructions": instructions,
        "details": details or {},
        "required": required,
    }


def build_starter_order_sets() -> list[dict]:
    """Curated starter content; facilities can clone/replace it under local governance."""
    return [
        {
            "set_code": "SET-ED-SEPSIS-INITIAL",
            "name": "Emergency sepsis — initial bundle",
            "specialty": "Emergency Medicine",
            "encounter_types": ["EMERGENCY", "OUTPATIENT", "INPATIENT"],
            "description": "Initial diagnostics, monitoring and treatment prompts for suspected sepsis. Clinician review remains mandatory.",
            "items": [
                _set_item("LABORATORY", "Complete blood count", priority="STAT", indication="Suspected sepsis", required=True),
                _set_item("LABORATORY", "Comprehensive metabolic panel", priority="STAT", indication="Suspected sepsis"),
                _set_item("LABORATORY", "Serum lactate", priority="STAT", indication="Suspected sepsis", required=True),
                _set_item("LABORATORY", "Blood culture - aerobic", priority="STAT", indication="Suspected sepsis before antibiotics"),
                _set_item("LABORATORY", "Blood culture - anaerobic", priority="STAT", indication="Suspected sepsis before antibiotics"),
                _set_item("NURSING", "Sepsis observations", priority="STAT", indication="Suspected sepsis"),
                _set_item("MEDICATION", "Ceftriaxone - intravenous", priority="STAT", indication="Empiric antimicrobial therapy", details={"dose": "2 g", "route": "IV", "frequency": "Every 24 hours", "duration": "Review at 48–72 hours"}),
            ],
        },
        {
            "set_code": "SET-ED-CHEST-PAIN",
            "name": "Emergency chest pain",
            "specialty": "Emergency Medicine / Cardiology",
            "encounter_types": ["EMERGENCY", "OUTPATIENT"],
            "description": "Time-sensitive initial chest-pain evaluation with cardiac monitoring and serial diagnostics.",
            "items": [
                _set_item("CARDIOLOGY", "12-lead ECG", priority="STAT", indication="Acute chest pain", required=True),
                _set_item("LABORATORY", "High sensitivity troponin I", priority="STAT", indication="Acute chest pain", required=True),
                _set_item("LABORATORY", "Complete blood count", priority="URGENT", indication="Acute chest pain"),
                _set_item("LABORATORY", "Renal function panel", priority="URGENT", indication="Acute chest pain"),
                _set_item("IMAGING", "Portable chest X-ray", priority="URGENT", indication="Acute chest pain"),
                _set_item("NURSING", "Cardiac telemetry", priority="STAT", indication="Acute chest pain"),
            ],
        },
        {
            "set_code": "SET-STROKE-INITIAL",
            "name": "Acute stroke — initial pathway",
            "specialty": "Neurology / Emergency Medicine",
            "encounter_types": ["EMERGENCY", "INPATIENT"],
            "description": "Immediate imaging, glucose, coagulation and neurologic observation orders for suspected acute stroke.",
            "items": [
                _set_item("IMAGING", "CT head without contrast", priority="STAT", indication="Suspected acute stroke", required=True),
                _set_item("LABORATORY", "Random blood glucose", priority="STAT", indication="Suspected acute stroke", required=True),
                _set_item("LABORATORY", "Complete blood count", priority="STAT", indication="Suspected acute stroke"),
                _set_item("LABORATORY", "Prothrombin time and INR", priority="STAT", indication="Thrombolysis safety assessment"),
                _set_item("LABORATORY", "Activated partial thromboplastin time", priority="STAT", indication="Thrombolysis safety assessment"),
                _set_item("NURSING", "Neurological observations", priority="STAT", indication="Suspected acute stroke"),
                _set_item("NURSING", "Aspiration precautions", priority="STAT", indication="Stroke swallow safety"),
            ],
        },
        {
            "set_code": "SET-ADULT-ADMISSION",
            "name": "Adult inpatient admission",
            "specialty": "General Medicine",
            "encounter_types": ["INPATIENT"],
            "description": "Core admission, nursing, mobility, nutrition and safety orders. Tailor every item to the patient.",
            "items": [
                _set_item("ADT", "Admit to inpatient service", indication="Inpatient care required", required=True),
                _set_item("NURSING", "Vital signs monitoring", instructions="Record at least every 4 hours; escalate per early warning score."),
                _set_item("NURSING", "Early warning score monitoring"),
                _set_item("NURSING", "Fall precautions"),
                _set_item("ACTIVITY", "Activity as tolerated"),
                _set_item("DIET", "Regular diet"),
                _set_item("NURSING", "Pain assessment and reassessment"),
            ],
        },
        {
            "set_code": "SET-DIABETES-FOLLOWUP",
            "name": "Diabetes follow-up",
            "specialty": "Endocrinology / Primary Care",
            "encounter_types": ["OUTPATIENT", "TELEHEALTH"],
            "description": "Routine diabetes monitoring and complication screening starter set.",
            "items": [
                _set_item("LABORATORY", "HbA1c", indication="Diabetes monitoring"),
                _set_item("LABORATORY", "Renal function panel", indication="Diabetes monitoring"),
                _set_item("LABORATORY", "Urine albumin/creatinine ratio", indication="Diabetic kidney screening"),
                _set_item("LABORATORY", "Lipid profile", indication="Cardiovascular risk monitoring"),
                _set_item("CONSULT", "Nutrition and dietetics consult", indication="Diabetes education and nutrition plan"),
            ],
        },
        {
            "set_code": "SET-ANTENATAL-INITIAL",
            "name": "Antenatal initial assessment",
            "specialty": "Obstetrics",
            "encounter_types": ["OUTPATIENT", "MATERNITY"],
            "description": "Initial antenatal laboratory and imaging starter set, subject to gestational age and national guidance.",
            "items": [
                _set_item("LABORATORY", "Complete blood count", indication="Initial antenatal assessment"),
                _set_item("LABORATORY", "Blood group and Rh typing", indication="Initial antenatal assessment"),
                _set_item("LABORATORY", "HIV rapid test", indication="Antenatal screening with consent"),
                _set_item("LABORATORY", "Hepatitis B surface antigen", indication="Antenatal screening"),
                _set_item("LABORATORY", "Syphilis RPR", indication="Antenatal screening"),
                _set_item("LABORATORY", "Urinalysis", indication="Initial antenatal assessment"),
                _set_item("IMAGING", "Obstetric ultrasound - dating", indication="Pregnancy dating and viability"),
            ],
        },
        {
            "set_code": "SET-POSTOPERATIVE-CARE",
            "name": "Postoperative ward care",
            "specialty": "Surgery",
            "encounter_types": ["INPATIENT", "DAY_CASE"],
            "description": "Postoperative monitoring, mobility, respiratory care and wound-safety starter orders.",
            "items": [
                _set_item("NURSING", "Postoperative monitoring", priority="URGENT", indication="Postoperative care"),
                _set_item("NURSING", "Pain assessment and reassessment", indication="Postoperative care"),
                _set_item("RESPIRATORY", "Incentive spirometry", indication="Postoperative pulmonary care"),
                _set_item("ACTIVITY", "Ambulate with assistance", indication="Postoperative mobility"),
                _set_item("NURSING", "Wound care", indication="Postoperative incision care"),
                _set_item("DIET", "Clear liquid diet"),
            ],
        },
        {
            "set_code": "SET-DISCHARGE-CORE",
            "name": "Discharge readiness and follow-up",
            "specialty": "Care Coordination",
            "encounter_types": ["OUTPATIENT", "EMERGENCY", "INPATIENT", "DAY_CASE"],
            "description": "Medication reconciliation, education, summary and follow-up coordination before discharge.",
            "items": [
                _set_item("DISCHARGE", "Medication reconciliation at discharge", indication="Discharge readiness", required=True),
                _set_item("DISCHARGE", "Patient education at discharge", indication="Discharge readiness", required=True),
                _set_item("DISCHARGE", "Generate discharge summary", indication="Discharge readiness", required=True),
                _set_item("DISCHARGE", "Follow-up appointment request", indication="Post-discharge continuity"),
            ],
        },
    ]


def seed_order_sets(db: Session) -> int:
    existing = set(db.scalars(select(OrderSet.set_code)).all())
    active_codes = set(db.scalars(select(OrderCatalogItem.orderable_code).where(OrderCatalogItem.active.is_(True))).all())
    inserted = 0
    for payload in build_starter_order_sets():
        if payload["set_code"] in existing:
            continue
        items = [item for item in payload["items"] if item["orderable_code"] in active_codes]
        if not items:
            continue
        order_set = OrderSet(
            set_code=payload["set_code"],
            name=payload["name"],
            description=payload["description"],
            specialty=payload["specialty"],
            encounter_types_json=json.dumps(payload["encounter_types"]),
            source="UMOJA_STARTER",
            created_by="Umoja Clinical Content Team",
            approved_by="Umoja Clinical Governance",
        )
        db.add(order_set)
        db.flush()
        for sequence, item in enumerate(items):
            db.add(OrderSetItem(
                order_set_id=order_set.id,
                orderable_code=item["orderable_code"],
                sequence=sequence,
                selected_by_default=True,
                required=item["required"],
                default_priority=item["default_priority"],
                default_indication=item["default_indication"],
                default_instructions=item["default_instructions"],
                details_json=json.dumps(item["details"]),
            ))
        inserted += 1
    if inserted:
        db.commit()
    return len(existing) + inserted


def seed_order_catalog(db: Session) -> int:
    rows = build_order_catalog()
    existing_codes = set(db.scalars(select(OrderCatalogItem.orderable_code)).all())
    missing = [row for row in rows if row["orderable_code"] not in existing_codes]
    if missing:
        db.bulk_insert_mappings(OrderCatalogItem, missing)
        db.commit()
    seed_order_sets(db)
    return len(existing_codes) + len(missing)
