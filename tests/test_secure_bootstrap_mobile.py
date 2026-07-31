from pathlib import Path

def test_login_has_no_prefilled_credentials():
    html=Path("frontend/index.html").read_text()
    js=Path("frontend/app.js").read_text()
    assert "value=\"admin\"" not in html
    assert "demo-accounts" not in js
    assert "data-demo-username" not in js
    assert "firstRunPanel" in html
    assert "setup-admin" in js

def test_compose_uses_generated_secret_files():
    review=Path("docker-compose.review.yml").read_text()
    prod=Path("docker-compose.production.yml").read_text()
    assert "POSTGRES_PASSWORD:" not in review
    assert "UMOJA_DB_PASSWORD:" not in review
    assert "review_bootstrap_token" in review
    assert "bootstrap_admin_password" not in prod
    assert "bootstrap_token" in prod

def test_mobile_breakpoints_and_private_cache_policy():
    css=Path("frontend/styles.css").read_text()
    sw=Path("frontend/service-worker.js").read_text()
    assert "@media(max-width:900px)" in css
    assert "@media(max-width:600px)" in css
    assert "mobile-nav-open" in css
    assert "url.pathname.startsWith('/api/')" in sw

def test_no_patient_identifier_persisted_in_local_storage():
    js=Path("frontend/app.js").read_text()
    save_line=next(line for line in js.splitlines() if "umojaAfyaEnterpriseState" in line and "setItem" in line)
    assert "selectedPatientId" not in save_line
