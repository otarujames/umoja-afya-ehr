from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "frontend/app.js").read_text()
CSS = (ROOT / "frontend/styles.css").read_text()
TRACKER = (ROOT / "backend/app/routers/tracker.py").read_text()


def test_background_refresh_is_five_minutes_but_lock_heartbeat_is_not_relaxed():
    assert "const APP_REFRESH_INTERVAL_MS = 5 * 60 * 1000" in JS
    assert "setInterval(pollWorkflowNotifications,APP_REFRESH_INTERVAL_MS)" in JS
    assert "setInterval(v5RefreshMessageCount,APP_REFRESH_INTERVAL_MS)" in JS
    assert "setInterval(v106RefreshSafe,APP_REFRESH_INTERVAL_MS)" in JS
    assert "heartbeat`,{method:'POST'" in JS
    assert "}},60000)" in JS


def test_rooming_is_encounter_controlled_and_does_not_start_provider_time():
    assert "v10163RoomingModal" in JS
    assert "General Practice Room" in JS
    assert "activity_type:'ROOMING'" in JS
    assert "if(status==='TRIAGED')await move('READY_FOR_PROVIDER')" in JS
    assert "if(status==='READY_FOR_PROVIDER')await move('ROOMED')" in JS
    assert "payload.status == EncounterStatus.IN_PROGRESS" in TRACKER
    assert "payload.status in {EncounterStatus.ROOMED, EncounterStatus.IN_PROGRESS}" not in TRACKER


def test_patient_care_surfaces_triage_complete_and_roomed_patients():
    assert "v10163CareReadyBoard" in JS
    assert "Triage completed" in JS
    assert "Awaiting room or provider" in JS
    assert "Placed and ready" in JS
    assert 'data-v1016-action="tracker-room"' in JS
    assert 'data-v1016-action="provider-workflow"' in JS


def test_today_patient_actions_are_reachable_and_roster_is_relocated():
    final_today = JS.rsplit("renderTodayPatients=async function(){", 1)[1].split("\n};", 1)[0]
    assert "v10163-action-dock" in final_today
    assert "v10163-action-column" in final_today
    assert "v10163-roster-drawer" in final_today
    assert 'data-v7-splitter="1"' not in final_today
    assert ".v10163-action-dock{position:sticky" in CSS
    assert ".v10163-action-column{position:sticky" in CSS


def test_recent_patient_memory_is_scoped_and_visible_in_lookup_workspaces():
    assert "v10163RecentPatientLookup" in JS
    assert "Recents & Favorites" in JS
    assert "Recent records" in JS
    assert "Recently viewed" in JS
    assert "state.countryCode||'country'" in JS
    assert "state.facility||'facility'" in JS
    assert "v104RememberPatient(patient)" in JS

