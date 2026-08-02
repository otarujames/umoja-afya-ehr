# Umoja Afya Enterprise EHR — Production Release 11.0.0

Umoja Afya is a provider-facing, record-centric, multi-country enterprise Electronic Health Record. This release supports country-isolated practice contexts for Tanzania, Kenya, Nigeria, Pakistan and Rwanda across public, private and faith-based health systems. The package contains the application, PostgreSQL persistence, database migrations, production and review Docker profiles, unit-first capacity management, longitudinal clinical documentation, workqueues, scheduling, Registration/ADT, emergency and specialty workflows, clinical device integration foundations, country-sensitive payments and a self-hosted clinical audio-transcription service.

This is not a patient-portal product and it is not packaged as an MVP. The default `docker-compose.yml` is the hardened production topology. Release archives contain no fixed passwords. Initialization generates a protected local credential roster and startup provisions it idempotently.

## 11.0.0 access and VPS deployment repair

Release 11.0.0 fixes the login-crashing missing `Facility` import in `backend/app/access_control.py`. It removes the browser-driven first-administrator and setup-secret mechanism from the API, frontend, configuration, OpenAPI contract, Compose files and initialization scripts. Production initialization now generates random credentials locally for 41 role-appropriate accounts: one global `platform.admin` superuser plus administrator, registration, physician, nursing, pharmacy, laboratory, finance and operations users for Tanzania, Kenya, Nigeria, Pakistan and Rwanda. Existing database passwords and an existing generated manifest are preserved during upgrades; access matrices are repaired without silently resetting credentials.

For the hosted service, `scripts/deploy-vps-traefik.sh` targets `https://umojaehr.online/`, validates the existing `traefik-59qx-traefik-1` container, uses the external `traefik` Docker network, disables the bundled nginx proxy and confirms both internal and public readiness before reporting success. See `docs/RELEASE_11_0_0_ACCESS_AND_TRAEFIK.md`.

## 10.16.3 patient access, rooming and persistent workflow actions

Version 10.16.3 keeps the selected patient's next valid front-desk action outside the scrolling worklist, moves on-duty teams and service points into a compact expandable operations drawer, and adds encounter-controlled rooming during or after triage. The room defaults to **General Practice Room** but remains editable; room placement does not start provider time. Patient Care now exposes separate completed-triage and roomed lists, and patient lookup workspaces show recently viewed records scoped to the signed-in user, country and facility. Routine background refresh runs every five minutes while the clinical activity-lock heartbeat remains at its safer one-minute cadence. See `docs/RELEASE_10_16_3_PATIENT_ACCESS.md`.

Release 10.16.2 added Pakistan and Rwanda as complete countries of practice rather than decorative landing choices. Each receives a governed facility directory, country and facility access scopes, review identities, currency and local payment channels, login branding, country ambience and generated country-administrator roles. The landing experience is also smaller and more playful: a compact five-country selector sits beneath a brighter, responsive care-context hero while hospital names remain protected until authentication. See `docs/COUNTRY_CONTEXTS_10_16_2.md`.

Release 10.16.2 made Patient Station lookup live, token-aware and progressively ranked within the active country context. Patient Tracker can start triage and provider review directly in the selected encounter. The provider workspace adds a post-triage sequence with HPI, a body-mapped 14-system review-by-exception ROS, examination, assessment and plan; all physical care writes require a live encounter and historical visits are deliberately review-only. Primary navigation now follows the patient journey from Scheduling and Registration/ADT into Patient Care, Health Records, ancillary care and Billing.

The full flowsheet workspace is a permanent time-row/variable-column spreadsheet. Authorized users can add, remove and reorder governed variable columns or apply a compact preset without losing prior observations. Inpatient-only columns stay visible but locked until the selected encounter has an active admission order, with matching API enforcement.

Registration now reuses the selected longitudinal record instead of repeating MPI lookup. It includes a governed electronic-consent catalog with signer, witness, language, encounter, timestamp and SHA-256 evidence provenance. Billing adds editable draft estimates, explicit finalization, encounter-linked collections, cash/change, card-terminal authorization, bank/gateway settlement references, local mobile-money Lipa/till QR instructions and crypto wallet/network QR instructions. See `docs/RELEASE_10_16_ENCOUNTER_WORKFLOWS.md` before deployment.

Orders now use a smart CPOE workspace with live tokenized lookup, category facets, favorites/recent shortcuts, adaptive clinical and operational details, governed order panels, a reviewed basket and atomic multi-order signing. The starter catalog contains 1,095 extensible orderables and eight curated panels; local administrators with configuration authority can add approved orderables and versioned panels with an audited governance reason. See `docs/RELEASE_10_16_SMART_CPOE.md`.

## 10.15.1 chart and encounter integrity release

Release 10.15.1 adds an always-visible, searchable 244-variable flowsheet spreadsheet to the patient Chart Summary, spanning triage, ambulatory, inpatient and specialty care. Inpatient rows require an active Admit to inpatient service order for the selected encounter, enforced in both the browser and API. Flowsheet encounters are selected from real patient encounters or created through a controlled workflow; ENC identifiers are never accepted from free text and are generated by the server.

## 10.15.1 installable encrypted offline release

Release 10.15.1 installs from the HTTPS browser as a PWA, keeps approved patient records and eligible transactions in a PIN-protected AES-GCM device vault, synchronizes an ordered outbox after reconnection, and prevents duplicate replays with server-side idempotency receipts. Server passwords and bearer tokens are not stored offline; signatures, medication administration, discharge, death recording and other high-risk actions remain online-only. See `docs/RELEASE_10_15_OFFLINE_PWA.md`.

## 10.14.0 record-centred workflow release

Release 10.14.0 rebuilt Patient Station around one selected longitudinal record, connected the audited print center, distinguished encounter workflows from record-only calls/refills/counseling, exposed signed-note provenance, made flowsheet variables editable, and added country-sensitive billing, payment plans, collections and mobile-money/crypto references. See `docs/RELEASE_10_14.md`.

## 10.11.0 shipping hardening

Release 10.11.0 adds build-time Alembic graph validation, a VPS preflight gate, controlled one-off production migration execution, corrected Docker image versioning, and removal of bundled runtime databases. See `docs/VPS_PRODUCTION_SHIPPING_10_11.md`.

## Multi-country practice context

Version 10.11.0 introduced the pre-login practice-context boundary; version 10.16.2 extended it to Tanzania, Kenya, Nigeria, Pakistan and Rwanda. Country selection changes identity, facility scope and local workflow context but does not grant access. Authentication verifies the selected country against each user's Country × Facility access matrix. Facility and unit lists remain available only after login through Change Context.

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
- Bundles a private `faster-whisper` service. Review and CPU-VPS production default to the `small` model; `medium` or `large-v3` remain opt-in after validating memory, storage, latency and (ideally) GPU capacity.

## Docker review

Generate local review secrets and a protected local user roster:

```bash
./scripts/init-review.sh
docker compose -f docker-compose.review.yml up --build
```

Open `http://localhost:8000`. Initial account credentials are in `secrets/review_preloaded_users.json`; protect the file, distribute credentials individually and delete working copies after storing them in an approved password vault. Every generated account requires a password change and MFA enrollment.

The first transcription downloads the selected Whisper model into the named model-cache volume. The rest of the EHR remains available while the transcription service initializes.

## Production initialization

```bash
chmod +x scripts/*.sh
./scripts/init-production.sh
```

Then protect `.env` and `secrets/` using operating-system access controls and backup procedures. For the Umoja Afya VPS, start through its existing Traefik:

```bash
./scripts/deploy-vps-traefik.sh
```

For a standalone host without Traefik, edit `.env`, install `deploy/tls/fullchain.pem` and `deploy/tls/privkey.pem`, then start the bundled nginx topology:

```bash
./scripts/deploy-production.sh
```

The default production topology is:

```text
Client → TLS Nginx reverse proxy → FastAPI application → PostgreSQL
                                      └──────────────→ private transcription service
```

PostgreSQL and application secrets are mounted as Docker secrets. The deployment-generated account roster is mounted read-only and synchronized idempotently during startup. Do not place a raw password inside `DATABASE_URL`.

### Existing Traefik on a VPS

When ports 80/443 are already owned by Traefik, use the supplied overlay. It disables the bundled nginx host-port service and attaches the app to the configured external Traefik network:

```bash
./scripts/deploy-vps-traefik.sh
```

The VPS profile defaults to `https://umojaehr.online/`, Traefik container `traefik-59qx-traefik-1`, external network `traefik` and certificate resolver `letsencrypt`. Override them in `.env` only when the host infrastructure changes.

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
