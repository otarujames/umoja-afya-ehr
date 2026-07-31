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
- Added pre-login country-of-practice landing page for Tanzania, Kenya, and Nigeria.
- Moved all facility selection behind authentication into country-scoped Change Context.
- Added country-level user access grants and cross-country login denial with audit events.
- Added Kenya and Nigeria ministry branding and facility contexts.
- Added country-specific synthetic review patients and identifiers.
- Added country filtering to patient lookup and facility APIs.

## 10.10.0

- Repaired baseline administrator access synchronization across Tanzania, Kenya and Nigeria.
- Ensured `platform.admin` receives all active facilities, all three countries, and the complete administrator function and department catalogs.
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
