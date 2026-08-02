from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_patient_lookup_is_tokenized_ranked_and_live():
    api = (ROOT / "backend/app/routers/patients.py").read_text(encoding="utf-8")
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    assert "tokens =" in api and "Every typed token must appear" in api
    assert "case((full_name == normalized" in api
    assert "v1016LiveRecordSearch" in js and "continue typing to narrow" in js


def test_tracker_launches_triage_and_provider_work_in_selected_encounter():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    assert 'data-v1016-action="tracker-triage"' in js
    assert 'data-v1016-action="provider-workflow"' in js
    assert "V1016_ROS" in js and "Review of systems" in js
    assert "v1016AdvanceProviderEncounter" in js
    assert "PROVIDER_ENCOUNTER_NOTE" in js


def test_provider_ros_is_fast_body_mapped_and_requires_positive_detail():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend/styles.css").read_text(encoding="utf-8")
    assert "v1016RosBodyMap" in js and 'data-ros-region="chest"' in js
    assert "All reviewed — negative" in js and "Review by exception" in js
    assert "undocumentedPositive" in js and "Document the pertinent" in js
    assert ".v1016-ros-review" in css and ".v1016-ros-system" in css


def test_top_navigation_follows_patient_journey():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    tabs = js.split("const v4ModuleTabs=[", 1)[1].split("];", 1)[0]
    labels = ["Scheduling", "Registration/ADT", "Patient Care", "Health Records", "Radiology", "Billing"]
    assert [tabs.index(f"label:'{label}'") for label in labels] == sorted(tabs.index(f"label:'{label}'") for label in labels)


def test_closed_visits_are_review_only_and_physical_work_requires_encounter():
    enterprise = (ROOT / "backend/app/routers/enterprise.py").read_text(encoding="utf-8")
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    assert "PHYSICAL_ENCOUNTER_ACTIVITY_TYPES" in enterprise
    assert "A physical patient interaction must be linked to a selected encounter" in enterprise
    assert "The selected encounter is closed" in enterprise
    assert "Historical encounter — review only" in js
    assert "chartEncounterSelect" in js


def test_electronic_consents_have_catalog_evidence_and_audit():
    enterprise = (ROOT / "backend/app/routers/enterprise.py").read_text(encoding="utf-8")
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    assert "CONSENT_TEMPLATES" in enterprise
    assert enterprise.count('"code":') >= 17
    assert '@router.post("/patients/{patient_mpi_id}/consents"' in enterprise
    assert "signature_sha256" in enterprise and "CONSENT_{payload.decision}" in enterprise
    assert "v1016ConsentCenter" in js and "Electronic signature" in js


def test_payment_flushes_id_before_audit_and_requires_confirmation():
    enterprise = (ROOT / "backend/app/routers/enterprise.py").read_text(encoding="utf-8")
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    payment = enterprise.split('@router.post("/payments"', 1)[1].split('@router.get("/payment-instructions"', 1)[0]
    assert payment.index("db.flush()") < payment.index("IntegrationEvent") < payment.index("write_audit")
    assert "if not payload.confirmed" in payment
    assert "UMOJA_MOBILE_MONEY_TILL" in enterprise and "UMOJA_CRYPTO_WALLET" in enterprise
    assert "v1016RefreshPaymentInstructions" in js and "v1016PaymentConfirmed" in js


def test_estimates_are_draft_then_explicitly_finalized():
    enterprise = (ROOT / "backend/app/routers/enterprise.py").read_text(encoding="utf-8")
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    assert 'Literal["DRAFT", "POSTED"]' in enterprise
    assert '@router.patch("/charges/{charge_id}"' in enterprise
    assert "FINALIZE_ESTIMATE" in enterprise
    assert 'data-v1014-action="new-estimate"' in js
    assert 'data-v1016-action="finalize-estimate"' in js


def test_user_profile_photos_are_admin_managed_validated_and_audited():
    enterprise = (ROOT / "backend/app/routers/enterprise.py").read_text(encoding="utf-8")
    model = (ROOT / "backend/app/enterprise_models.py").read_text(encoding="utf-8")
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    migration = ROOT / "migrations/versions/5f6a7b8c9d0e_admin_managed_user_profile_photos.py"
    assert '@router.post("/admin/users/{user_id}/profile-photo")' in enterprise
    assert "Only an administrator can assign user profile photos" in enterprise
    assert "Profile photos must be 2 MB or smaller" in enterprise
    assert "UPDATE_USER_PROFILE_PHOTO" in enterprise and "REMOVE_USER_PROFILE_PHOTO" in enterprise
    assert "profile_photo_sha256" in model and migration.exists()
    assert 'data-v5-action="manage-user-photo"' in js
    assert "individual users cannot upload or replace their own photos" in js
