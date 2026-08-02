from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_pwa_install_assets_and_api_cache_boundary():
    manifest = (ROOT / "frontend/manifest.json").read_text(encoding="utf-8")
    worker = (ROOT / "frontend/service-worker.js").read_text(encoding="utf-8")
    main = (ROOT / "backend/app/main.py").read_text(encoding="utf-8")
    assert '"id": "/"' in manifest
    assert "umoja-192.png" in manifest and "umoja-512.png" in manifest and "maskable" in manifest
    assert "url.pathname.startsWith('/api/')" in worker
    assert "API data is deliberately never placed in Cache Storage" in worker
    assert '@app.get("/offline.js"' in main
    for icon in ("umoja-192.png", "umoja-512.png", "umoja-maskable-512.png"):
        assert (ROOT / "frontend/assets/icons" / icon).is_file()


def test_official_logo_is_used_for_app_favicon_and_install_icons():
    html = (ROOT / "frontend/index.html").read_text(encoding="utf-8")
    worker = (ROOT / "frontend/service-worker.js").read_text(encoding="utf-8")
    assert "/assets/umoja-logo-full.png" in html
    assert html.count("/assets/umoja-logo-mark.png") >= 2
    assert "/assets/icons/favicon.ico" in html
    assert "/assets/icons/apple-touch-icon.png" in html
    for asset in (
        "frontend/assets/umoja-logo-full.png",
        "frontend/assets/umoja-logo-mark.png",
        "frontend/assets/icons/favicon.ico",
        "frontend/assets/icons/apple-touch-icon.png",
    ):
        assert (ROOT / asset).is_file()
        assert f"/{asset.removeprefix('frontend/')}" in worker


def test_offline_vault_encrypts_cache_outbox_and_pin_wrapped_key():
    offline = (ROOT / "frontend/offline.js").read_text(encoding="utf-8")
    assert "AES-GCM" in offline
    assert "PBKDF2_ITERATIONS = 310000" in offline
    assert "wrapped_key" in offline
    assert "server password" not in offline.lower()
    assert "session token" not in offline.lower()
    assert "cacheResponse" in offline and "cachedResponse" in offline
    assert "X-Idempotency-Key" in offline
    assert "NEEDS_REVIEW" in offline


def test_high_risk_workflows_are_online_only():
    offline = (ROOT / "frontend/offline.js").read_text(encoding="utf-8")
    for pattern in ("sign|addendum", "orders", "results", "medications", "discharge", "break-glass"):
        assert pattern in offline
    assert "This safety-critical workflow requires an online connection" in offline


def test_server_idempotency_and_device_registry_are_migrated_and_audited():
    middleware = (ROOT / "backend/app/middleware.py").read_text(encoding="utf-8")
    router = (ROOT / "backend/app/routers/offline.py").read_text(encoding="utf-8")
    migration = (ROOT / "migrations/versions/4e5f6a7b8c9d_offline_devices_and_idempotency.py").read_text(encoding="utf-8")
    assert "class IdempotencyMiddleware" in middleware
    assert "OFFLINE_MUTATION_RECONCILED" in middleware
    assert "This offline device is not enrolled or has been revoked" in middleware
    assert "OFFLINE_DEVICE_ENROLLED" in router and "OFFLINE_SYNC_COMPLETED" in router
    assert 'down_revision = "3d4e5f6a7b8c"' in migration
    assert '"offline_device"' in migration and '"idempotency_receipt"' in migration
