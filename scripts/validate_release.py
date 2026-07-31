#!/usr/bin/env python3
from pathlib import Path
import compileall, json, subprocess, sys, yaml
ROOT=Path(__file__).resolve().parents[1]
errors=[]
if not compileall.compile_dir(ROOT/"backend",quiet=1): errors.append("Python compilation failed")
for f in [ROOT/"frontend/app.js",ROOT/"frontend/service-worker.js"]:
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
 "clean_release_image": "umoja-afya-ehr:10.12.0" in (ROOT/"docker-compose.production.yml").read_text(),
}
errors.extend([name for name,ok in checks.items() if not ok])
report={"release":"10.12.0","checks":checks,"errors":errors}
(ROOT/"release-validation.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
sys.exit(1 if errors else 0)
