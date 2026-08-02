from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_smart_cpoe_frontend_has_catalog_panels_composer_and_atomic_basket():
    js = (ROOT / "frontend/app.js").read_text(encoding="utf-8")
    css = (ROOT / "frontend/styles.css").read_text(encoding="utf-8")
    for marker in (
        "v1016QueueOrderSearch",
        "v1016OrderDetailFields",
        "v1016OrderSetCards",
        "v1016OrderBasket",
        "Review and Sign Orders",
        "'/orders/batch'",
        "Create Governed Orderable",
        "Create Custom Order Panel",
    ):
        assert marker in js
    assert ".v1016-cpoe-shell" in css
    assert "@media (max-width:620px)" in css


def test_cpoe_backend_enforces_encounter_and_structured_medication_safety():
    router = (ROOT / "backend/app/routers/orders.py").read_text(encoding="utf-8")
    schema = (ROOT / "backend/app/schemas.py").read_text(encoding="utf-8")
    model = (ROOT / "backend/app/models.py").read_text(encoding="utf-8")
    assert "CLOSED_ENCOUNTER_STATUSES" in router
    assert "Medication order requires" in router
    assert '@router.post("/orders/batch"' in router
    assert "db.rollback()" in router
    assert "class OrderBatchIn" in schema
    assert "details_json" in model and "orderable_code" in model


def test_governed_orderables_and_order_sets_are_admin_controlled_and_migrated():
    enhancements = (ROOT / "backend/app/routers/enhancements.py").read_text(encoding="utf-8")
    rbac = (ROOT / "backend/app/rbac.py").read_text(encoding="utf-8")
    seed = (ROOT / "backend/app/catalog_seed.py").read_text(encoding="utf-8")
    migration = ROOT / "migrations/versions/6a7b8c9d0e1f_enterprise_cpoe_order_sets.py"
    assert "_require_catalog_admin" in enhancements
    assert "system.configuration.manage" in enhancements
    assert '@router.post("/order-catalog"' in enhancements
    assert '@router.post("/order-sets"' in enhancements
    assert 'path.startswith("/api/v1/order-catalog")' in rbac
    assert "build_starter_order_sets" in seed
    for code in ("SET-ED-SEPSIS-INITIAL", "SET-ED-CHEST-PAIN", "SET-ADULT-ADMISSION", "SET-ANTENATAL-INITIAL"):
        assert code in seed
    assert migration.is_file()
    text = migration.read_text(encoding="utf-8")
    assert 'down_revision = "5f6a7b8c9d0e"' in text
    assert '"order_set"' in text and '"order_set_item"' in text
