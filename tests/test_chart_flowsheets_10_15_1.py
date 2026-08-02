from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


def test_chart_summary_contains_searchable_governed_flowsheet_grid():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend/styles.css").read_text(encoding="utf-8")
    assert "renderChartFlowSpreadsheet" in js
    assert "data-chart-flow-input" in js
    assert "chartFlowScope" in js and "chartFlowSearch" in js
    assert "saveChartFlowEntries" in js
    assert ".chart-flow-table-wrap" in css
    assert ".chart-flow-entry" in css


def test_triage_through_inpatient_templates_are_available():
    config = yaml.safe_load((ROOT / "config/flowsheet-templates.yml").read_text(encoding="utf-8"))
    codes = {template["code"] for template in config["templates"]}
    assert config["version"] == "11.0.0"
    assert {"TRIAGE_AMBULATORY", "ADULT_INPATIENT", "PAEDIATRIC_INPATIENT", "NEONATAL", "ICU_DEVICE"} <= codes
    row_count = sum(len(group.get("rows", [])) for template in config["templates"] for group in template.get("groups", []))
    assert row_count >= 200


def test_flowsheet_encounter_is_selected_or_server_generated():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    schemas = (ROOT / "backend/app/schemas.py").read_text(encoding="utf-8")
    tracker = (ROOT / "backend/app/routers/tracker.py").read_text(encoding="utf-8")
    models = (ROOT / "backend/app/models.py").read_text(encoding="utf-8")
    assert "data-flowsheet-encounter-select" in js
    assert '<input id="v5FsEncounter"' not in js
    assert "resolveFlowsheetEncounter" in js
    assert "class EncounterCreateIn" in schemas and "encounter_id" not in schemas.split("class EncounterCreateIn", 1)[1].split("class DischargeIn", 1)[0]
    assert '@router.post("/patients/{patient_mpi_id}/encounters"' in tracker
    assert 'default=lambda: new_id("ENC")' in models


def test_permanent_flowsheet_uses_time_rows_and_configurable_variable_columns():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend/styles.css").read_text(encoding="utf-8")
    api = (ROOT / "backend/app/routers/flowsheets.py").read_text(encoding="utf-8")
    assert "A permanent time-by-variable spreadsheet" in js
    assert "v1016FlowTimeRows" in js and "Configure Flowsheet Columns" in js
    assert 'data-v5-action="save-flow-row"' in js and 'data-v5-action="apply-flow-preset"' in js
    assert "_inpatient_only_parameters" in api and "_enforce_observation_scope" in api
    assert "Flowsheet observations require a selected patient encounter" in api
    assert "Historical encounters are review-only" in api
    assert ".v1016-flow-table" in css and ".v1016-flow-active-columns" in css


def test_inpatient_rows_require_a_live_admit_order_in_ui_and_api():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    api = (ROOT / "backend/app/routers/flowsheets.py").read_text(encoding="utf-8")
    catalog = (ROOT / "backend/app/catalog_seed.py").read_text(encoding="utf-8")
    assert "CHART_INPATIENT_TEMPLATES" in js and "chartHasAdmitOrder" in js
    assert api.count("_enforce_inpatient_scope") >= 3
    assert "INPATIENT_TEMPLATE_CODES" in api
    assert "Admit to inpatient service" in catalog
    assert "existing_codes" in catalog and "missing" in catalog
