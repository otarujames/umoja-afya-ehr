# Umoja Afya Enterprise EHR 10.7.0 — Release Validation

Validation was completed against the unpacked release source on 30 July 2026.

## Security and credential controls

- No database file, patient database snapshot, user account, password hash or active session is included in the archive.
- Login username and password fields are blank; the frontend contains no automatic credential fill logic.
- The legacy demonstration-account endpoint is absent from the runtime API and OpenAPI specification.
- Fresh review seeding created synthetic clinical data with **zero user accounts**.
- The first administrator was created successfully through the one-time token-protected setup endpoint.
- An invalid setup token was rejected with HTTP 403.
- A second bootstrap attempt after administrator creation was rejected with HTTP 409.
- The newly chosen administrator credentials authenticated successfully and received the administrator access matrix.
- Docker review and production Compose profiles use generated secret files rather than fixed database, security or account passwords.
- Legacy seeded-account signatures are disabled during prestart and their sessions are revoked.

## Mobile and browser controls

- Responsive breakpoints are present for tablet, mobile and small-phone layouts.
- Mobile navigation uses an off-canvas rail and backdrop.
- Module navigation is horizontally scrollable on narrow screens.
- Login and first-run forms collapse to one column.
- Complex grids and three-pane workspaces stack vertically.
- Modal workflows become touch-friendly bottom sheets.
- Touch controls use minimum 44-pixel targets.
- Clinical API responses and authenticated transactions are excluded from service-worker caching.
- Selected patient identifiers are not persisted in localStorage.

## Engineering validation

| Validation | Result |
|---|---:|
| Pytest release checks | 4 passed |
| Python compilation | Passed |
| Frontend JavaScript syntax | Passed |
| Service-worker JavaScript syntax | Passed |
| YAML documents parsed | 29 |
| OpenAPI paths | 110 |
| Fresh Alembic migration chain | Passed |
| Fresh review prestart | Passed |
| User accounts after review seed | 0 |
| First-run administrator setup | Passed |
| Invalid setup-token rejection | Passed |
| Repeat-bootstrap rejection | Passed |
| Administrator login after setup | Passed |
| Database files shipped | 0 |

## Environment limitation

A Docker engine was not available in the artifact-generation environment. Docker Compose YAML, startup scripts, migrations, secret wiring, application APIs and frontend assets were validated independently. The final container launch must still be performed on the target Docker host.

## Release 10.7 preloaded-user validation

- Deployment-time password generation: passed
- No embedded passwords in frontend or Compose: passed
- Platform administrator roster entry: passed
- Tanzania, Kenya, Nigeria, Pakistan and Rwanda country-administrator entries: passed
- Country-specific registration, physician, nurse, pharmacy, laboratory, finance and operations entries: passed
- Mandatory first-login password change: enabled
- MFA requirement: enabled
- Country and facility access isolation: configured
- Idempotent restart behavior without password reset: implemented
- Automated tests: 8 passed

## 10.8 multicultural data and landing validation

- Synthetic review population seeded successfully: **15,000 patients**.
- Practice-context distribution: Tanzania 11,467; Kenya 1,967; Nigeria 1,566.
- Name cultures represented: Tanzanian, Kenyan, Nigerian, Ugandan and South African.
- Ugandan and South African review records are represented as cross-border residents/visitors inside compatible authorized TZ/KE/NG/RW contexts.
- Country isolation remains enforced through `country_code`.
- Compact landing page passed HTML/CSS integration and mobile-breakpoint review.
- Automated tests: 8 passed.
- Python compilation and frontend JavaScript syntax passed.
