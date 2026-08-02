# Secure Bootstrap and Mobile Responsiveness — 10.7.0

## Credential handling

- The application ships with no active administrator, no demo users and no prefilled username or password.
- Database passwords, application signing secrets and first-run setup tokens are randomly generated outside the application image.
- The first administrator is created once through `/api/v1/auth/setup-admin`, protected by a random one-time setup token.
- When an active administrator exists, the setup endpoint permanently rejects additional bootstrap attempts.
- Older demonstration accounts matching the prior release signatures are disabled during prestart and their sessions are revoked.
- User passwords are entered only during account setup/reset and are stored as Argon2id hashes.

## Mobile behavior

- Responsive header, horizontally scrollable module bar and off-canvas navigation at tablet/mobile widths.
- Touch targets are at least 44 px, forms collapse to one column and modals become bottom sheets.
- Tables remain independently horizontally scrollable instead of overlapping adjacent panels.
- Complex three-pane clinical workspaces stack vertically below 1100 px.
- Patient identifiers are no longer persisted in localStorage.
- The service worker does not cache API responses or authenticated clinical transactions.
