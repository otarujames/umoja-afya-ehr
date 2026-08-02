# Release 10.16.3

- Kept each selected patient's next valid action in a visible workflow dock above the Today’s Patients table and made the table action column sticky.
- Moved On-Duty Teams & Service Points out of the far-right work area into a compact expandable operations drawer.
- Changed routine notification, message-count and workspace background refresh to five minutes while preserving the one-minute clinical activity-lock heartbeat.
- Added encounter-controlled rooming during and after triage with an editable **General Practice Room** default.
- Separated room placement from provider start time; provider time now begins only when the encounter enters `IN_PROGRESS`.
- Added dedicated Patient Care lists for completed-triage patients awaiting placement and roomed patients ready for provider review.
- Added user-, country- and facility-scoped recently viewed patients to Patient Station and patient lookup workspaces.
- Added responsive styling for the persistent action dock, rooming lanes, recent-patient shortcuts and relocated roster drawer.
- Added Pakistan and Rwanda as fully authorized countries of practice with country-scoped facilities, administrators, synthetic review identities and access-matrix options.
- Added PKR with Raast, Easypaisa, JazzCash and 1LINK payment choices, plus RWF with MTN MoMo, Airtel Money and IremboPay choices.
- Added Pakistan and Rwanda login branding, flag assets, country ambience and offline context preservation.
- Rebuilt the landing page around a brighter, more playful hero and a much smaller responsive five-country selector while keeping facility directories behind authentication.
- Added live, tokenized Patient Station lookup that ranks partial name, MRN, MPI, telephone and national-ID matches as the query narrows.
- Added direct Start Triage and Provider Review actions to Patient Tracker, preserving the selected patient and encounter.
- Added a structured provider workflow with post-triage context, HPI, physical examination, assessment, plan, draft/sign controls and encounter progression.
- Rebuilt the 14-system Review of Systems as a responsive body-system map with explicit one-click negative review, review-by-exception status cycling, positive-finding details and a save guard that prevents undocumented positive findings.
- Reordered the primary workflow navigation to Scheduling, Registration/ADT, Patient Care, Health Records, Radiology, Billing, Reports, Tools and Settings.
- Rebuilt the full flowsheet workspace as a permanent time-row/variable-column spreadsheet with encounter switching, configurable/reorderable columns, a compact template picker and a new-row entry line that remains visible before the first observation.
- Added API enforcement for inpatient-only variables in mixed custom flowsheets so browser bypass cannot chart them without an active admission order.
- Made historical encounters explicitly review-only and enforced an API guard that requires a live encounter for every physical patient interaction.
- Preserved deliberate selection of previous encounters for review while preventing new care from being silently written into a closed visit.
- Made Registration/ADT edit the already-selected longitudinal record without repeating patient search.
- Added a 17-form electronic-consent catalog with online signer decisions, relationship, witness, language, encounter linkage, timestamp, audit trail and SHA-256 signature evidence.
- Added draft visit estimates, authorized finalization, billed-to responsibility, encounter/account collections and auditable reconciliation.
- Fixed the Collect Payment server error by flushing the payment identifier before writing dependent integration and audit records.
- Added verified cash-drawer/change, card-terminal, bank/gateway, mobile-money Lipa/till QR and crypto wallet/network QR workflows without storing PAN, CVV, PINs or private keys.
- Improved narrow Patient Station, provider, consent, payment, chart-encounter and unit-context wrapping and responsive layout.
- Added administrator-only user profile-photo assignment/removal with PNG/JPEG/WebP validation, a 2 MB limit, authenticated display, SHA-256 provenance and security audit events; individual users cannot upload their own photo.
- Rebuilt Orders as a live, token-narrowing CPOE workspace with category facets, Favorites, Recent, an adaptive order composer and a persistent reviewed signing basket.
- Added structured medication, laboratory, blood-bank, imaging, consultation, nursing, ADT and operational order details with API-side medication and active-encounter validation.
- Added atomic batch signing so a multi-order panel cannot be partially committed.
- Added 1,095 extensible starter orderables plus eight versioned, governed starter panels containing 49 selected orders across sepsis, chest pain, stroke, admission, diabetes, antenatal, postoperative and discharge workflows.
- Added administrator-only custom orderable and order-panel authoring with governance reason, approval provenance, stable codes, versioning and audit events.

# Release 10.15.1

- Adopted the supplied Umoja Afya heart-and-pulse artwork as the application mark, full EHR brand lockup, browser favicon, Apple touch icon and installable PWA icon set.
- Repaired Patient Station layout clipping, long-label wrapping and zoom behavior while preserving the existing three-pane design.
- Added a searchable, spreadsheet-style Chart Flowsheet to the patient Chart Summary with 244 governed triage, ambulatory, inpatient and specialty variables.
- Added a triage and ambulatory template covering arrival, acuity, vitals, safety screening and point-of-care measurements.
- Locked inpatient observation entry unless the same encounter has an active Admit to inpatient service order, with matching server-side enforcement on sheet creation and observation writes.
- Replaced free-text flowsheet encounter IDs with real encounter selection and a controlled Create new encounter path whose ENC identifier is generated by the server.
- Added the Admit to inpatient service orderable and changed catalog seeding to add missing governed orderables to existing deployments.
- Added standards-based browser PWA installation with 192px, 512px and maskable icons, standalone display and patient-workflow shortcuts.
- Added an opt-in AES-GCM encrypted IndexedDB record cache and mutation outbox protected by a separate PBKDF2-derived offline PIN.
- Added a configurable 24-hour offline access lease, per-user device enrollment/revocation and visible Sync Center.
- Added offline support for registration, arrivals, triage, record activities, draft notes, flowsheets, payments and draft billing transactions.
- Kept signatures, medications, orders, results, discharge, death recording, break-glass access and administration online-only.
- Added sequential reconnect replay, per-user idempotency receipts, duplicate protection, device audit provenance and explicit Needs Review reconciliation.
- Ensured the service worker caches only the application shell; patient API responses remain inside the encrypted vault.

# Release 10.14.0

- Rebuilt Patient Station around one selected longitudinal record, with registration/chart access and a visible patient/activity/encounter storyboard.
- Connected Print Forms to the audited print preview and history workflow.
- Added scheduled arrival, walk-in, triage, record-only refill and phone-call actions.
- Added visible signed-note provenance and editable, audited flowsheet variables.
- Rebuilt record-linked billing with billed-to, claims, counseling, payment plans, country-sensitive currency, local mobile money and crypto references.
- Added patient/encounter consistency checks and a Traefik overlay that avoids host port conflicts.

# Release 10.7.0

- Added exclusive patient-activity locks with five-minute heartbeat expiry.
- Added permission requests, yes/no handoff, denial reason and timeframe.
- Added automatic transfer to the oldest pending requester after lock expiry.
- Added database-enforced idempotency for non-repeatable patient workflows.
- Added 60-second AJAX workspace refresh and request polling.
- Added hover-to-discover contextual guidance for actions and icons.

# Release 10.7.0

- Added functional Pinned and Recent sections to the activity launcher.
- Added per-user activity favorites and recent-workspace history.
- Rebuilt Patient Search & MPI as a Patient Station-style three-pane lookup.
- Added patient favorites, recently opened records, patient preview, Patient Station and Chart actions.
- Preserved record-context enforcement and existing audit-backed chart access.

# Release 10.7.0

- Removed all preloaded login usernames and passwords from the runtime product.
- Replaced automatic administrator creation with token-protected, one-time first-run setup.
- Replaced fixed Docker review secrets with randomly generated secret files.
- Disabled legacy demonstration accounts during production/review prestart.
- Added mobile/off-canvas navigation, touch-safe controls, responsive forms and stacked workspaces.
- Prevented the service worker from caching API responses or authenticated clinical transactions.
- Removed patient identifiers from persistent browser localStorage.

## 10.7.0
- Added pre-login country-of-practice landing page, extended in 10.16.2 to Tanzania, Kenya, Nigeria, Pakistan and Rwanda.
- Moved all facility selection behind authentication into country-scoped Change Context.
- Added country-level user access grants and cross-country login denial with audit events.
- Added Kenya and Nigeria ministry branding and facility contexts.
- Added country-specific synthetic review patients and identifiers.
- Added country filtering to patient lookup and facility APIs.

## 10.10.0

- Repaired baseline administrator access synchronization across the configured practice countries; 10.16.2 added Pakistan and Rwanda.
- Ensured `platform.admin` receives all active facilities, all five countries, and the complete administrator function and department catalogs.
- Ensured country administrators receive the complete administrator catalogs while remaining country-isolated.
- Added idempotent PowerShell and shell administrator-repair utilities.
- Added an explicit optional password reconciliation mode for review deployments where the generated manifest and existing database account diverged.
- Revokes stale sessions after controlled password reconciliation so new tokens carry the corrected matrix.


## v10.10.0
- Redesigned Pinned and Recent activity launcher sections.
- Added compact activity cards, clear empty states, pin affordances, keyboard focus, and responsive spacing.

## 10.11.0

- Added mandatory Alembic graph validation during image build and prestart.
- Corrected stale 10.7.0 Docker image and configuration version tags.
- Added VPS production preflight and controlled migration deployment flow.
- Removed bundled SQLite runtime database and Python cache artifacts.
- Set review population target to 15,000 synthetic patients.
- Preserved non-root, read-only runtime and secret-file database credentials.
# Release 10.12.0

- Rebuilt the application launcher with compact Pinned and Recent cards and a
  responsive mobile layout that prevents letter-by-letter text wrapping.
- Made the status-bar facility identity react to the authenticated facility
  selector instead of displaying a static hospital.
- Added a glowing Umoja logo loading state, dark/system themes, density and
  accent preferences, and optional country-flag workspace ambience.
- Refined Patient Station proportions, typography and interactive feedback.
- Added an outbound-only model network for transcription downloads while
  retaining private database networking and unexposed internal services.
- Changed the CPU-VPS Whisper default to `small`; larger models remain opt-in.
- Forced clean image rebuilds so stale application images and migrations cannot
  survive an upgrade.
- Added reverse-proxy isolation headers while retaining TLS, Docker secrets,
  non-root containers, dropped capabilities and read-only filesystems.
