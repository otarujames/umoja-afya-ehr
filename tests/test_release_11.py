from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_access_control_imports_facility_used_by_login_access_resolution():
    source = (ROOT / "backend/app/access_control.py").read_text()
    assert "from .models import Facility" in source
    assert "select(Facility)" in source


def test_browser_and_api_setup_token_paths_are_removed():
    combined = "\n".join(
        (ROOT / path).read_text()
        for path in (
            "backend/app/routers/auth.py",
            "backend/app/config.py",
            "frontend/app.js",
            "frontend/index.html",
            "docker-compose.yml",
            "docker-compose.production.yml",
            "docker-compose.review.yml",
        )
    )
    for forbidden in ("bootstrap_token", "setup-admin", "setup-status", "firstRunPanel"):
        assert forbidden not in combined


def test_generated_roster_contains_exactly_one_global_superuser_and_roles():
    generator = (ROOT / "scripts/generate_preloaded_users.py").read_text()
    provisioner = (ROOT / "scripts/preload_users.py").read_text()
    assert '"username": "platform.admin"' in generator
    assert '"display_name": "Umoja Afya Global Superuser"' in generator
    assert '"superuser": True' in generator
    assert "exactly one manifest-designated global superuser" in provisioner
    for role in ("registration", "physician", "nurse", "pharmacy", "laboratory", "finance", "operations"):
        assert f'(\"{role}\",' in generator


def test_vps_deployment_targets_existing_traefik_and_public_url():
    script = (ROOT / "scripts/deploy-vps-traefik.sh").read_text()
    env = (ROOT / ".env.production.example").read_text()
    overlay = (ROOT / "docker-compose.traefik.yml").read_text()
    assert "traefik-59qx-traefik-1" in script
    assert "https://${UMOJA_PUBLIC_HOST}/api/v1/health" in script
    assert "UMOJA_PUBLIC_HOST=umojaehr.online" in env
    assert "traefik.http.services.umoja-afya.loadbalancer.server.port" in overlay
    assert "profiles: [standalone-proxy]" in overlay

