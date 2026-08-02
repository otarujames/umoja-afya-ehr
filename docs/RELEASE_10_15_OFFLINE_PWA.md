# Umoja Afya EHR 10.15.1 — Installable Offline PWA

Release 10.15.1 turns the provider-facing web application into an installable
Progressive Web App (PWA) with a controlled encrypted offline workspace. The
central PostgreSQL database remains the legal source of truth.

## Browser installation

The production URL must use HTTPS. After deployment, open the EHR in a supported
browser:

- Chrome or Edge on Windows/macOS: select **Install Umoja Afya** in the address
  bar or use **Install** inside the EHR sync control.
- Chrome on Android: choose **Install app** or **Add to Home screen**.
- Safari on iPhone/iPad: use **Share → Add to Home Screen**.

Installation adds the application shell, icon, standalone window and shortcuts.
It does not place database credentials or a copy of the central database on the
device.

## Enabling an authorized offline device

1. Sign in online with the assigned institutional account.
2. Open **Online / Sync** in the application header.
3. Choose **Enable protected offline access**.
4. Name the managed device and create a separate 6–12 digit offline PIN.
5. Confirm the institutional-device declaration.
6. Open the patient records required for the current assignment while online.

The device receives a server-side enrollment record and audit event. Patient
responses subsequently viewed by the authorized user are cached in an AES-GCM
encrypted IndexedDB vault. The data-encryption key is wrapped with a key derived
from the offline PIN using PBKDF2-SHA-256 with 310,000 iterations. The account
password and bearer token are never stored in the vault.

The default offline lease is 24 hours and can be configured from 1 to 72 hours:

```dotenv
UMOJA_OFFLINE_ACCESS_ENABLED=true
UMOJA_OFFLINE_LEASE_HOURS=24
UMOJA_OFFLINE_MAX_PENDING=1000
```

## Offline workflows

Approved transactions are encrypted locally and added to the device outbox:

- patient registration;
- scheduled arrival and walk-in arrival;
- encounter status updates used by triage;
- phone call, refill, triage and financial-counseling activities;
- draft note creation and draft editing;
- flowsheet creation, controls and observations;
- draft charges and claims;
- payments and payment-plan activities;
- selected workqueue actions.

Safety-critical transactions remain online-only so current authorization,
concurrency and clinical guardrails can be checked immediately:

- note signature, addendum and cosign;
- clinical orders and diagnostic-result acknowledgement;
- medication orders, verification and administration;
- discharge, patient-death recording and break-glass access;
- claim submission/status change;
- system administration and audio uploads.

## Synchronization and duplicate prevention

Each queued mutation has a cryptographically random operation ID. On reconnect,
the unlocked app replays transactions in recorded order using that ID as the
server idempotency key. The server reserves and stores a replay receipt per user
and operation, preventing duplicate payments, notes, arrivals or observations
when a request is retried after a network interruption.

The server re-runs normal authentication, RBAC, facility access, patient/
encounter consistency and workflow validation. A rejected or ambiguous item is
not silently discarded; it remains in **Needs Review** in the Sync Center with
its protected reconciliation message. Every reconciled offline mutation writes
an audit event with user, facility, device, original offline time, endpoint and
result.

Because the encryption key exists only after PIN unlock, synchronization runs
automatically when connectivity returns while the installed app is open and
unlocked. If the app was closed or the online session expired, reopen it, unlock
the vault and sign in online; synchronization resumes without recreating the
transaction.

## Device safeguards

- Use managed institutional devices with screen lock and full-device encryption.
- Configure remote wipe and mobile-device management where available.
- Do not enable offline access on shared public computers.
- Lock the vault or sign out when handing the device to another user.
- Revoke a lost device from the user/device administration process.
- Synchronize and reconcile all pending work before removing local data.
- Include offline-device loss in the incident-response and breach-assessment
  procedures.

PWA encryption reduces risk but does not replace organizational safeguards,
clinical validation, DPIA/privacy review, penetration testing or local regulatory
approval for storing patient data on endpoint devices.

## Deployment

Release 10.15.1 adds Alembic revision `4e5f6a7b8c9d`, creating the enrolled-device
registry and idempotency receipts. Normal production prestart applies the
migration.

For a VPS using the supplied Traefik overlay:

```bash
docker compose -f docker-compose.production.yml -f docker-compose.traefik.yml config --quiet
docker compose -f docker-compose.production.yml -f docker-compose.traefik.yml up -d --build --remove-orphans
docker compose -f docker-compose.production.yml -f docker-compose.traefik.yml ps
```

After deployment, reload the site once while online so the 10.15 service worker
replaces the older shell cache.
