# Umoja Afya Enterprise EHR — Production Release 10.11.0

Umoja Afya is a provider-facing, record-centric enterprise Electronic Health Record for Tanzania's public, private and faith-based health system. This package contains the application, PostgreSQL persistence, database migrations, production and review Docker profiles, unit-first capacity management, longitudinal clinical documentation, workqueues, scheduling, Registration/ADT, emergency and specialty workflows, clinical device integration foundations, bilingual English/Kiswahili support, and a self-hosted clinical audio-transcription service.

This is not a patient-portal product and it is not packaged as an MVP. The default `docker-compose.yml` is the hardened production topology. A separate review profile supplies synthetic clinical records only; it creates no users or passwords.

## 10.11.0 shipping hardening

Release 10.11.0 adds build-time Alembic graph validation, a VPS preflight gate, controlled one-off production migration execution, corrected Docker image versioning, and removal of bundled runtime databases. See `docs/VPS_PRODUCTION_SHIPPING_10_11.md`.

## Multi-country practice context

Version 10.11.0 adds real-time patient-activity locking, permission-based handoff, idempotent workflow controls, 60-second AJAX refresh, and hover-to-discover guidance. Version 10.11.0 introduced a pre-login country selector for Tanzania, Kenya, and Nigeria. Country selection changes ministry branding only; it does not grant access. Authentication verifies the selected country against each user's Country × Facility access matrix. Facility and unit lists remain available only after login through Change Context.

Review data includes country-specific synthetic names, identifiers, telephone formats, coverage labels, and facility directories.

## Major 10.2 corrections

- Eliminates malformed inline PostgreSQL URLs by constructing the connection URL from discrete fields and Docker secret files. Passwords containing `@`, `#`, `:`, `/` and other reserved characters are encoded safely by SQLAlchemy.
- Removes Uvicorn development reload mode from review and production containers.
- Applies Alembic migrations under a PostgreSQL advisory lock before serving traffic.
- Adds liveness/readiness probes, startup retries, non-root/read-only containers, isolated database networking, bounded logs and controlled production bootstrap.
- Repairs **+ New Note** so it always opens the record-linked Clinical Documentation composer.
- Adds **Create & Sign** for a new note while retaining draft, signature, cosign and addendum controls.
- Adds a complete Clinical Audio Annotation Studio with microphone recording, pause/resume/stop, audio upload, playback, English/Kiswahili transcription, confidence, engine/model provenance, low-confidence warnings and source-audio-session linkage to the signed note.
- Raw clinical audio is discarded after transcription by default. Transcript, hash, size, duration, confidence and audit provenance are retained.
- Bundles a private `faster-whisper` service. Review defaults to the `small` model; production defaults to `large-v3` and can be moved to a validated GPU node.

## Docker review

No account or password is preloaded. Generate local secrets and complete first-run setup:

```bash
./scripts/init-review.sh
docker compose -f docker-compose.review.yml up --build
```

Open `http://localhost:8000` and complete secure first-run setup using the random token printed by `init-review.sh` or `init-review.ps1`.

The first transcription downloads the selected Whisper model into the named model-cache volume. The rest of the EHR remains available while the transcription service initializes.

## Production initialization

```bash
chmod +x scripts/*.sh
./scripts/init-production.sh
```

Then:

1. Edit `.env` and set the public host, allowed hosts and CORS origin.
2. Install `deploy/tls/fullchain.pem` and `deploy/tls/privkey.pem`.
3. Protect `.env` and `secrets/` using operating-system access controls and backup procedures.
4. Start the stack:

```bash
./scripts/deploy-production.sh
```

The default production topology is:

```text
Client → TLS Nginx reverse proxy → FastAPI application → PostgreSQL
                                      └──────────────→ private transcription service
```

PostgreSQL, application secrets and the one-time bootstrap token are mounted as Docker secrets. Do not place a raw password inside `DATABASE_URL`.

## Deployment diagnostics

```bash
./scripts/diagnose-deployment.sh docker-compose.production.yml
```

Useful commands:

```bash
docker compose -f docker-compose.production.yml ps
docker compose -f docker-compose.production.yml logs --tail=200 app db transcription proxy
curl -k https://YOUR-HOST/api/v1/health/ready
```

## Clinical audio controls

The audio workflow requires an active patient and encounter. The user must confirm the facility's recording/consent policy before capture. Server transcription produces an unsigned draft only. The UI displays transcription confidence and provenance and requires the clinician to compare the transcript against the recording before saving or signing. Cross-patient or cross-encounter audio-session linkage is rejected by the API.

## Production boundary

The package is engineered for controlled production deployment, but no software archive can by itself confer HIPAA compliance, SOC 2 attestation, ISO certification or authorization for live clinical care. The deploying organization remains responsible for DPIA/risk analysis, clinical-safety review, identity-provider integration, MFA, penetration testing, validated interfaces, data migration, disaster-recovery testing, workforce procedures, audit evidence and formal go-live acceptance.

See:

- `docs/SECURE_BOOTSTRAP_AND_MOBILE_10_2.md`
- `docs/PRODUCTION_DEPLOYMENT_AND_AUDIO_FIXES_10_1.md`
- `docs/OPERATIONS_RUNBOOK.md`
- `docs/PRODUCTION_READINESS_CHECKLIST.md`
- `docs/COMPLIANCE_BOUNDARY.md`
- `docs/RELEASE_VALIDATION.md`


Audio upload transport: the application and TLS proxy use a 60 MB request ceiling for the 50 MB clinical-audio limit, with a 360-second transcription proxy timeout.


## Preloaded users

Release 10.7 provisions a deployment-generated baseline roster of platform, country-administrator and operational users. Passwords are random deployment secrets, never embedded or autofilled. See `docs/PRELOADED_USER_ROSTER_10_7.md`.

## Review data in 10.8

The review environment seeds 15,000 synthetic patient records with culturally varied Tanzanian, Kenyan, Nigerian, Ugandan and South African names. These records are synthetic and intended only for testing, workflow demonstrations and training. Country-context authorization remains enforced for all patient searches and clinical workspaces.
