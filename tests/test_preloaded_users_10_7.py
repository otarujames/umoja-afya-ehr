from pathlib import Path
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def test_generator_creates_country_scoped_roster(tmp_path):
    output = tmp_path / "users.json"
    subprocess.run([sys.executable, str(ROOT / "scripts/generate_preloaded_users.py"), "--output", str(output)], check=True)
    data = json.loads(output.read_text())
    users = {item["username"]: item for item in data["users"]}
    assert "platform.admin" in users
    assert {"TZ", "KE", "NG"} == set(users["platform.admin"]["country_codes"])
    assert users["tz.nurse"]["country_codes"] == ["TZ"]
    assert users["ke.physician"]["country_codes"] == ["KE"]
    assert users["ng.registration"]["country_codes"] == ["NG"]
    assert len(users) == 25
    assert all(len(item["password"]) >= 12 for item in users.values())


def test_no_passwords_are_embedded_in_compose_or_frontend():
    combined = "\n".join((ROOT / name).read_text() for name in ["docker-compose.review.yml", "docker-compose.production.yml", "frontend/index.html", "frontend/app.js"])
    assert "Umoja!2026" not in combined
    assert '"password":' not in combined
    assert "preloaded_users.json" in (ROOT / "docker-compose.production.yml").read_text()
