# Secure Provisioning and Mobile Responsiveness — 11.0.0

## Credential handling

- The release archive contains no fixed usernames, passwords or browser-visible credentials.
- Database passwords, application signing secrets and initial user passwords are randomly generated outside the application image.
- Initialization creates a protected `preloaded_users.json` roster with one global superuser plus country-scoped clinical, access, laboratory, pharmacy, finance and operations users.
- Startup provisions the roster idempotently and repairs authoritative access without resetting passwords for existing accounts.
- Browser-based administrator setup and setup-token endpoints do not exist in release 11.
- Older demonstration accounts matching the prior release signatures are disabled during prestart and their sessions are revoked.
- User passwords are entered only during account setup/reset and are stored as Argon2id hashes.

## Mobile behavior

- Responsive header, horizontally scrollable module bar and off-canvas navigation at tablet/mobile widths.
- Touch targets are at least 44 px, forms collapse to one column and modals become bottom sheets.
- Tables remain independently horizontally scrollable instead of overlapping adjacent panels.
- Complex three-pane clinical workspaces stack vertically below 1100 px.
- Patient identifiers are no longer persisted in localStorage.
- The service worker does not cache API responses or authenticated clinical transactions.
