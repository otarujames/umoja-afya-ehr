from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_landing_exposes_five_small_country_choices():
    html = (ROOT / "frontend/index.html").read_text()
    css = (ROOT / "frontend/styles.css").read_text()
    for code in ("TZ", "KE", "NG", "PK", "RW"):
        assert f'data-country-select="{code}"' in html
    assert "repeat(5,minmax(0,1fr))" in css
    assert "Start where care happens." in html


def test_pakistan_and_rwanda_are_complete_practice_contexts():
    seed = (ROOT / "backend/app/country_seed.py").read_text()
    app = (ROOT / "frontend/app.js").read_text()
    enterprise = (ROOT / "backend/app/routers/enterprise.py").read_text()
    for marker in ("PK-PIMS", "PK-JPMC", "RW-CHUK", "RW-KFH"):
        assert marker in seed
    for marker in ("code:'PKR'", "code:'RWF'", "PK:{name:'Pakistan'", "RW:{name:'Rwanda'"):
        assert marker in app
    assert '"code":"PK","label":"Pakistan"' in enterprise
    assert '"code":"RW","label":"Rwanda"' in enterprise


def test_country_flags_and_offline_ambience_exist():
    css = (ROOT / "frontend/styles.css").read_text()
    assert (ROOT / "frontend/assets/pakistan-flag.svg").exists()
    assert (ROOT / "frontend/assets/rwanda-flag.svg").exists()
    assert 'html[data-country="PK"]' in css
    assert 'html[data-country="RW"]' in css
