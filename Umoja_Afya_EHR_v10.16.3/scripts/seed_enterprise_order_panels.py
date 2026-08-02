from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import text

from backend.app.database import SessionLocal


PANELS = [
    {
        "set_code": "OPD-GENERAL-INITIAL",
        "name": "General Outpatient Initial Assessment",
        "specialty": "General Outpatient",
        "encounter_types": ["OUTPATIENT", "AMBULATORY"],
        "description": "Common outpatient evaluation and initial treatment orders.",
        "items": [
            "LAB-CBC",
            "LAB-CMP",
            "LAB-URINALYSIS",
            "LAB-HBA1C",
            "LAB-LIPID-PANEL",
            "IMG-CXR-2V",
            "MED-PARACETAMOL-500MG-TAB",
            "MED-IBUPROFEN-400MG-TAB",
        ],
    },
    {
        "set_code": "IP-ADMISSION-GENERAL",
        "name": "General Inpatient Admission",
        "specialty": "Inpatient Medicine",
        "encounter_types": ["INPATIENT"],
        "description": "Baseline admission, nursing, monitoring, diet and laboratory orders.",
        "items": [
            "LAB-CBC",
            "LAB-CMP",
            "LAB-URINALYSIS",
            "LAB-BLOOD-CULTURE",
            "IMG-CXR-PORTABLE",
            "NURS-VITALS-Q4H",
            "NURS-INTAKE-OUTPUT",
            "DIET-REGULAR",
            "ACTIVITY-UP-AD-LIB",
            "MED-PARACETAMOL-500MG-TAB",
            "MED-ONDANSETRON-4MG-IV",
        ],
    },
    {
        "set_code": "ED-INITIAL-EVALUATION",
        "name": "Emergency Department Initial Evaluation",
        "specialty": "Emergency Medicine",
        "encounter_types": ["EMERGENCY"],
        "description": "Emergency assessment, monitoring, laboratory and imaging starter panel.",
        "items": [
            "LAB-CBC",
            "LAB-CMP",
            "LAB-GLUCOSE",
            "LAB-TROPONIN",
            "LAB-LACTATE",
            "LAB-BLOOD-CULTURE",
            "IMG-CXR-PORTABLE",
            "IMG-CT-HEAD-NONCONTRAST",
            "CARD-ECG-12LEAD",
            "NURS-CARDIAC-MONITOR",
            "NURS-VITALS-Q15MIN",
            "MED-NORMAL-SALINE-1000ML-IV",
        ],
    },
    {
        "set_code": "ICU-GENERAL-ADMISSION",
        "name": "Adult ICU Admission",
        "specialty": "Critical Care",
        "encounter_types": ["INPATIENT", "ICU"],
        "description": "Critical-care monitoring, ventilation, laboratory and prophylaxis orders.",
        "items": [
            "LAB-CBC",
            "LAB-CMP",
            "LAB-ABG",
            "LAB-LACTATE",
            "LAB-MAGNESIUM",
            "LAB-PHOSPHATE",
            "IMG-CXR-PORTABLE",
            "NURS-VITALS-Q1H",
            "NURS-STRICT-INTAKE-OUTPUT",
            "NURS-NEURO-CHECK-Q1H",
            "RESP-VENTILATOR-MANAGEMENT",
            "MED-ENOXAPARIN-40MG-SC",
            "MED-PANTOPRAZOLE-40MG-IV",
        ],
    },
    {
        "set_code": "ONC-CHEMO-BASELINE",
        "name": "Oncology Treatment Baseline",
        "specialty": "Oncology",
        "encounter_types": ["OUTPATIENT", "INPATIENT", "INFUSION"],
        "description": "Baseline tests and supportive-care orders before systemic therapy.",
        "items": [
            "LAB-CBC-DIFF",
            "LAB-CMP",
            "LAB-LIVER-FUNCTION",
            "LAB-RENAL-FUNCTION",
            "LAB-MAGNESIUM",
            "LAB-PREGNANCY",
            "MED-ONDANSETRON-8MG-IV",
            "MED-DEXAMETHASONE-8MG-IV",
            "MED-NORMAL-SALINE-1000ML-IV",
        ],
    },
    {
        "set_code": "ONC-FEBRILE-NEUTROPENIA",
        "name": "Oncology Febrile Neutropenia",
        "specialty": "Oncology",
        "encounter_types": ["EMERGENCY", "INPATIENT"],
        "description": "Urgent evaluation and empiric-treatment support for suspected neutropenic sepsis.",
        "items": [
            "LAB-CBC-DIFF",
            "LAB-CMP",
            "LAB-LACTATE",
            "LAB-BLOOD-CULTURE-X2",
            "LAB-URINE-CULTURE",
            "IMG-CXR-PORTABLE",
            "MED-NORMAL-SALINE-1000ML-IV",
        ],
    },
    {
        "set_code": "MAT-LABOR-ADMISSION",
        "name": "Labor and Delivery Admission",
        "specialty": "Obstetrics",
        "encounter_types": ["INPATIENT", "LABOR_DELIVERY"],
        "description": "Maternal assessment, fetal monitoring and baseline admission orders.",
        "items": [
            "LAB-CBC",
            "LAB-BLOOD-TYPE-SCREEN",
            "LAB-URINALYSIS",
            "LAB-HIV",
            "LAB-SYPHILIS",
            "NURS-FETAL-MONITORING",
            "NURS-MATERNAL-VITALS",
            "MED-OXYTOCIN-INFUSION",
        ],
    },
    {
        "set_code": "PEDS-GENERAL-ADMISSION",
        "name": "Pediatric General Admission",
        "specialty": "Pediatrics",
        "encounter_types": ["INPATIENT", "PEDIATRIC"],
        "description": "Weight-based pediatric admission and monitoring panel.",
        "items": [
            "LAB-CBC",
            "LAB-CMP",
            "LAB-GLUCOSE",
            "LAB-URINALYSIS",
            "NURS-PEDS-VITALS-Q4H",
            "NURS-DAILY-WEIGHT",
            "NURS-INTAKE-OUTPUT",
        ],
    },
    {
        "set_code": "SURG-PREOPERATIVE",
        "name": "General Surgery Preoperative",
        "specialty": "Surgery",
        "encounter_types": ["INPATIENT", "OUTPATIENT", "SURGERY"],
        "description": "Standard preoperative evaluation and readiness panel.",
        "items": [
            "LAB-CBC",
            "LAB-CMP",
            "LAB-PT-INR",
            "LAB-BLOOD-TYPE-SCREEN",
            "CARD-ECG-12LEAD",
            "IMG-CXR-2V",
            "NURS-NPO",
            "NURS-SURGICAL-CONSENT",
        ],
    },
    {
        "set_code": "CARD-CHEST-PAIN",
        "name": "Cardiology Chest Pain",
        "specialty": "Cardiology",
        "encounter_types": ["EMERGENCY", "INPATIENT", "OUTPATIENT"],
        "description": "Assessment panel for suspected acute coronary syndrome.",
        "items": [
            "CARD-ECG-12LEAD",
            "LAB-TROPONIN",
            "LAB-CBC",
            "LAB-CMP",
            "LAB-LIPID-PANEL",
            "IMG-CXR-2V",
            "MED-ASPIRIN-81MG-TAB",
        ],
    },
    {
        "set_code": "RENAL-AKI",
        "name": "Acute Kidney Injury Evaluation",
        "specialty": "Nephrology",
        "encounter_types": ["INPATIENT", "OUTPATIENT", "EMERGENCY"],
        "description": "Renal laboratory, urine and imaging assessment panel.",
        "items": [
            "LAB-CMP",
            "LAB-RENAL-FUNCTION",
            "LAB-MAGNESIUM",
            "LAB-PHOSPHATE",
            "LAB-URINALYSIS",
            "LAB-URINE-PROTEIN-CREATININE",
            "IMG-RENAL-ULTRASOUND",
            "NURS-STRICT-INTAKE-OUTPUT",
        ],
    },
    {
        "set_code": "RESP-PNEUMONIA",
        "name": "Pneumonia Evaluation",
        "specialty": "Respiratory Medicine",
        "encounter_types": ["INPATIENT", "OUTPATIENT", "EMERGENCY"],
        "description": "Diagnostic and monitoring orders for suspected pneumonia.",
        "items": [
            "LAB-CBC",
            "LAB-CMP",
            "LAB-BLOOD-CULTURE",
            "LAB-SPUTUM-CULTURE",
            "IMG-CXR-2V",
            "NURS-PULSE-OXIMETRY",
            "RESP-OXYGEN-PROTOCOL",
        ],
    },
    {
        "set_code": "NEURO-STROKE",
        "name": "Acute Stroke Evaluation",
        "specialty": "Neurology",
        "encounter_types": ["EMERGENCY", "INPATIENT"],
        "description": "Time-sensitive acute neurological evaluation orders.",
        "items": [
            "IMG-CT-HEAD-NONCONTRAST",
            "CARD-ECG-12LEAD",
            "LAB-CBC",
            "LAB-CMP",
            "LAB-PT-INR",
            "LAB-GLUCOSE",
            "NURS-NEURO-CHECK-Q1H",
            "NURS-NPO-SWALLOW-SCREEN",
        ],
    },
    {
        "set_code": "MENTAL-HEALTH-ADMISSION",
        "name": "Behavioral Health Admission",
        "specialty": "Mental Health",
        "encounter_types": ["INPATIENT", "OUTPATIENT", "EMERGENCY"],
        "description": "Behavioral-health safety, screening and baseline medical orders.",
        "items": [
            "LAB-CBC",
            "LAB-CMP",
            "LAB-TSH",
            "LAB-URINE-TOXICOLOGY",
            "LAB-PREGNANCY",
            "NURS-SUICIDE-RISK-ASSESSMENT",
            "NURS-SAFETY-OBSERVATION",
        ],
    },
]


def main() -> None:
    db = SessionLocal()

    try:
        available = {
            row[0]
            for row in db.execute(
                text(
                    """
                    SELECT orderable_code
                    FROM order_catalog_item
                    WHERE active = true
                    """
                )
            )
        }

        now = datetime.now(timezone.utc)
        panels_created = 0
        items_created = 0
        missing_codes = set()

        for panel in PANELS:
            existing = db.execute(
                text(
                    """
                    SELECT id
                    FROM order_set
                    WHERE set_code = :set_code
                    """
                ),
                {"set_code": panel["set_code"]},
            ).scalar_one_or_none()

            if existing:
                order_set_id = existing
            else:
                order_set_id = db.execute(
                    text(
                        """
                        INSERT INTO order_set (
                            set_code,
                            name,
                            description,
                            specialty,
                            encounter_types_json,
                            version,
                            source,
                            active,
                            created_by,
                            approved_by,
                            approved_at,
                            created_at,
                            updated_at
                        )
                        VALUES (
                            :set_code,
                            :name,
                            :description,
                            :specialty,
                            :encounter_types_json,
                            1,
                            'UMOJA_ENTERPRISE_STARTER',
                            true,
                            'Umoja Clinical Content Team',
                            'Pending Local Clinical Governance',
                            NULL,
                            :created_at,
                            :updated_at
                        )
                        RETURNING id
                        """
                    ),
                    {
                        "set_code": panel["set_code"],
                        "name": panel["name"],
                        "description": panel["description"],
                        "specialty": panel["specialty"],
                        "encounter_types_json": json.dumps(
                            panel["encounter_types"]
                        ),
                        "created_at": now,
                        "updated_at": now,
                    },
                ).scalar_one()

                panels_created += 1

            for sequence, code in enumerate(
                panel["items"],
                start=1,
            ):
                if code not in available:
                    missing_codes.add(code)
                    continue

                exists = db.execute(
                    text(
                        """
                        SELECT 1
                        FROM order_set_item
                        WHERE order_set_id = :order_set_id
                          AND orderable_code = :orderable_code
                        """
                    ),
                    {
                        "order_set_id": order_set_id,
                        "orderable_code": code,
                    },
                ).first()

                if exists:
                    continue

                db.execute(
                    text(
                        """
                        INSERT INTO order_set_item (
                            order_set_id,
                            orderable_code,
                            sequence,
                            selected_by_default,
                            required,
                            default_priority,
                            default_indication,
                            default_instructions,
                            details_json
                        )
                        VALUES (
                            :order_set_id,
                            :orderable_code,
                            :sequence,
                            false,
                            false,
                            'ROUTINE',
                            NULL,
                            NULL,
                            '{}'
                        )
                        """
                    ),
                    {
                        "order_set_id": order_set_id,
                        "orderable_code": code,
                        "sequence": sequence,
                    },
                )

                items_created += 1

        db.commit()

        print("Panels created:", panels_created)
        print("Panel items created:", items_created)
        print("Catalog codes not yet available:", len(missing_codes))

        for code in sorted(missing_codes):
            print("MISSING:", code)

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
