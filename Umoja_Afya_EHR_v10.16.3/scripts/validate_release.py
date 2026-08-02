#!/usr/bin/env python3
from pathlib import Path
import compileall, json, subprocess, sys, yaml
ROOT=Path(__file__).resolve().parents[1]
errors=[]
if not compileall.compile_dir(ROOT/"backend",quiet=1): errors.append("Python compilation failed")
for f in [ROOT/"frontend/app.js",ROOT/"frontend/offline.js",ROOT/"frontend/service-worker.js"]:
    result=subprocess.run(["node","--check",str(f)],capture_output=True,text=True)
    if result.returncode: errors.append(result.stderr)
for f in list(ROOT.rglob("*.yml"))+list(ROOT.rglob("*.yaml")):
    try: yaml.safe_load(f.read_text())
    except Exception as exc: errors.append(f"{f}: {exc}")
html=(ROOT/"frontend/index.html").read_text(); js=(ROOT/"frontend/app.js").read_text(); review=(ROOT/"docker-compose.review.yml").read_text()
checks={
 "no_prefilled_login": "value=\"admin\"" not in html and "demo-accounts" not in js,
 "first_run_setup": "firstRunPanel" in html and "/auth/setup-admin" in js,
 "generated_review_secrets": "POSTGRES_PASSWORD:" not in review and "review_bootstrap_token" in review,
 "mobile_responsive": "mobile-nav-open" in (ROOT/"frontend/styles.css").read_text(),
 "api_not_cached": "url.pathname.startsWith('/api/')" in (ROOT/"frontend/service-worker.js").read_text(),
 "reactive_facility_status": 'id="statusFacilityName"' in html and "v1012UpdateFacilityContext" in js,
 "personalization": "V1012_PREF_KEY" in js and 'data-theme="dark"' in (ROOT/"frontend/styles.css").read_text(),
 "transcription_model_egress": "model_egress" in (ROOT/"docker-compose.production.yml").read_text(),
 "clean_release_image": "umoja-afya-ehr:10.16.3" in (ROOT/"docker-compose.production.yml").read_text(),
 "record_centred_patient_station": "v1014Storyboard" in js and "v1014RecordFinder" in js,
 "non_admin_station_resilience": "canSchedule?api" in js and "canRevenue?api" in js and "canNotes?api" in js,
 "functional_print_center": "v8OpenPrintWorkflow(v1014PatientRow" in js,
 "signed_note_provenance": "v1014-note-audit" in js and '"edit_history"' in (ROOT/"backend/app/routers/enterprise.py").read_text(),
 "country_sensitive_payments": "v1014Currency" in js and "Airtel Money" in js and "OPay" in js,
 "five_country_practice_context": all(f'data-country-select="{code}"' in html for code in ("TZ","KE","NG","PK","RW")) and all(code in (ROOT/"backend/app/country_seed.py").read_text() for code in ("PK-PIMS","RW-CHUK")),
 "pakistan_rwanda_payments": all(value in js for value in ("code:'PKR'","Raast","Easypaisa","code:'RWF'","MTN MoMo","IremboPay")),
 "compact_country_selector": "repeat(5,minmax(0,1fr))" in (ROOT/"frontend/styles.css").read_text() and "Start where care happens." in html,
 "traefik_overlay": (ROOT/"docker-compose.traefik.yml").exists(),
 "installable_pwa": '"id": "/"' in (ROOT/"frontend/manifest.json").read_text() and (ROOT/"frontend/assets/icons/umoja-512.png").exists(),
 "encrypted_offline_vault": "PBKDF2_ITERATIONS = 310000" in (ROOT/"frontend/offline.js").read_text() and "AES-GCM" in (ROOT/"frontend/offline.js").read_text(),
 "offline_api_not_shell_cached": "API data is deliberately never placed in Cache Storage" in (ROOT/"frontend/service-worker.js").read_text(),
 "idempotent_offline_replay": "IdempotencyMiddleware" in (ROOT/"backend/app/middleware.py").read_text() and (ROOT/"migrations/versions/4e5f6a7b8c9d_offline_devices_and_idempotency.py").exists(),
 "chart_flowsheet_spreadsheet": "renderChartFlowSpreadsheet" in js and "data-chart-flow-input" in js,
 "controlled_flowsheet_encounter": "data-flowsheet-encounter-select" in js and "resolveFlowsheetEncounter" in js and '<input id="v5FsEncounter"' not in js,
 "server_generated_encounter": "create_patient_encounter" in (ROOT/"backend/app/routers/tracker.py").read_text() and 'default=lambda: new_id("ENC")' in (ROOT/"backend/app/models.py").read_text(),
 "inpatient_admit_guard": "_enforce_inpatient_scope" in (ROOT/"backend/app/routers/flowsheets.py").read_text() and "Admit to inpatient service" in (ROOT/"backend/app/catalog_seed.py").read_text(),
 "official_brand_assets": all((ROOT/path).exists() for path in ["frontend/assets/umoja-logo-full.png","frontend/assets/umoja-logo-mark.png","frontend/assets/icons/favicon.ico","frontend/assets/icons/apple-touch-icon.png"]) and "/assets/icons/favicon.ico" in html,
 "ranked_live_patient_lookup": "v1016LiveRecordSearch" in js and "tokens =" in (ROOT/"backend/app/routers/patients.py").read_text(),
 "tracker_direct_clinical_actions": 'data-v1016-action="tracker-triage"' in js and 'data-v1016-action="provider-workflow"' in js,
 "provider_ros_workflow": "V1016_ROS" in js and "PROVIDER_ENCOUNTER_NOTE" in js,
 "provider_body_ros": "v1016RosBodyMap" in js and "Review by exception" in js and "undocumentedPositive" in js,
 "patient_journey_navigation": all(js.index(label) < js.index(next_label) for label,next_label in zip(["label:'Scheduling'","label:'Registration/ADT'","label:'Patient Care'","label:'Health Records'","label:'Radiology'"],["label:'Registration/ADT'","label:'Patient Care'","label:'Health Records'","label:'Radiology'","label:'Billing'"])),
 "permanent_configurable_flowsheet": "A permanent time-by-variable spreadsheet" in js and "v1016FlowColumnModal" in js and "_enforce_observation_scope" in (ROOT/"backend/app/routers/flowsheets.py").read_text(),
 "encounter_write_guard": "PHYSICAL_ENCOUNTER_ACTIVITY_TYPES" in (ROOT/"backend/app/routers/enterprise.py").read_text() and "Historical encounter — review only" in js,
 "electronic_consent_evidence": "CONSENT_TEMPLATES" in (ROOT/"backend/app/routers/enterprise.py").read_text() and "signature_sha256" in (ROOT/"backend/app/routers/enterprise.py").read_text(),
 "confirmed_payment_workflow": "db.flush()  # payment_id must exist" in (ROOT/"backend/app/routers/enterprise.py").read_text() and "v1016PaymentConfirmed" in js,
 "draft_estimate_finalization": "FINALIZE_ESTIMATE" in (ROOT/"backend/app/routers/enterprise.py").read_text() and 'data-v1016-action="finalize-estimate"' in js,
 "admin_managed_profile_photos": "Only an administrator can assign user profile photos" in (ROOT/"backend/app/routers/enterprise.py").read_text() and 'data-v5-action="manage-user-photo"' in js and (ROOT/"migrations/versions/5f6a7b8c9d0e_admin_managed_user_profile_photos.py").exists(),
 "smart_cpoe_workspace": "v1016OrderDetailFields" in js and "v1016OrderBasket" in js and "Create Governed Orderable" in js,
 "atomic_order_batch": '@router.post("/orders/batch"' in (ROOT/"backend/app/routers/orders.py").read_text() and "CLOSED_ENCOUNTER_STATUSES" in (ROOT/"backend/app/routers/orders.py").read_text(),
 "governed_order_sets": "build_starter_order_sets" in (ROOT/"backend/app/catalog_seed.py").read_text() and (ROOT/"migrations/versions/6a7b8c9d0e1f_enterprise_cpoe_order_sets.py").exists(),
 "five_minute_background_refresh": "const APP_REFRESH_INTERVAL_MS = 5 * 60 * 1000" in js and "setInterval(v106RefreshSafe,APP_REFRESH_INTERVAL_MS)" in js and "setInterval(pollWorkflowNotifications,APP_REFRESH_INTERVAL_MS)" in js,
 "encounter_controlled_rooming": "v10163RoomingModal" in js and "General Practice Room" in js and "activity_type:'ROOMING'" in js and "payload.status == EncounterStatus.IN_PROGRESS" in (ROOT/"backend/app/routers/tracker.py").read_text(),
 "patient_care_ready_lists": "v10163CareReadyBoard" in js and "Awaiting room or provider" in js and "Placed and ready" in js,
 "reachable_today_actions": "v10163-action-dock" in js and "v10163-action-column" in js and "v10163-roster-drawer" in js,
 "scoped_recent_patient_lookup": "v10163RecentPatientLookup" in js and "Recents & Favorites" in js and "state.countryCode||'country'" in js and "state.facility||'facility'" in js,
}
errors.extend([name for name,ok in checks.items() if not ok])
report={"release":"10.16.3","checks":checks,"errors":errors}
(ROOT/"release-validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
sys.exit(1 if errors else 0)
