from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_patient_station_is_record_centered_and_print_is_functional():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    start = js.index("renderPatientStationV5=async function(){")
    end = js.index("function v1014ActivityModal", start)
    station = js[start:end]
    assert "/today-patients" not in station
    assert "/workqueues/summary" not in station
    assert "v1014RecordFinder" in station
    assert "v1014Storyboard" in station
    assert "canSchedule?api" in station
    assert "canRevenue?api" in station
    assert "canNotes?api" in station
    assert "print-forms" in station
    assert "v8OpenPrintWorkflow(v1014PatientRow" in js


def test_record_only_actions_do_not_require_an_encounter():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    assert "REFILL_REQUEST" in js
    assert "PHONE_CALL" in js
    assert "record_only:!(link&&encounter)" in js
    assert "encounter_id:link&&encounter?encounter.encounter_id:null" in js


def test_note_provenance_and_patient_encounter_integrity_are_visible():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    api = (ROOT / "backend/app/routers/enterprise.py").read_text(encoding="utf-8")
    flowsheets = (ROOT / "backend/app/routers/flowsheets.py").read_text(encoding="utf-8")
    migration = (ROOT / "migrations/versions/3d4e5f6a7b8c_transaction_currency.py").read_text(encoding="utf-8")
    assert "v1014-note-audit" in js
    assert '"edit_history": visible_edits' in api
    assert api.count("Encounter does not belong to the selected patient") >= 4
    assert "Encounter does not belong to the selected patient" in flowsheets
    assert '"currency_code"' in api
    assert '("charge", "claim", "payment")' in migration


def test_country_payments_mobile_layout_and_traefik_overlay():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend/styles.css").read_text(encoding="utf-8")
    traefik = (ROOT / "docker-compose.traefik.yml").read_text(encoding="utf-8")
    for token in ("TZS", "KES", "NGN", "PKR", "RWF", "M-Pesa", "OPay", "Raast", "MTN MoMo", "USDT"):
        assert token in js
    assert "@media(max-width:760px)" in css
    assert ".v1014-station-layout" in css
    assert "profiles: [standalone-proxy]" in traefik
    assert "traefik.http.routers.umoja-afya.tls.certresolver" in traefik
