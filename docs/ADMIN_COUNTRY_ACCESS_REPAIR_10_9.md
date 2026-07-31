# Administrator country and access-matrix repair — 10.9.0

Release 10.9.0 corrects two upgrade-state problems:

1. A deployment credential manifest could contain a password that no longer matched an already-provisioned database account because normal startup intentionally preserved existing passwords.
2. An administrator created or modified by an earlier release could retain stale custom grants, making the account appear as an administrator while exposing only a minimal function and department set.

## Correct administrator scope

- `platform.admin`: full administrator function and department catalogs, every active facility, and Tanzania, Kenya, and Nigeria country contexts.
- `tz.admin`: full administrator function and department catalogs, all active Tanzanian facilities, Tanzania only.
- `ke.admin`: full administrator function and department catalogs, all active Kenyan facilities, Kenya only.
- `ng.admin`: full administrator function and department catalogs, all active Nigerian facilities, Nigeria only.

Country administrators remain isolated to their assigned country. Only an administrator explicitly granted several countries may cross country contexts.

## Windows review repair

From the extracted release folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\repair-admin-access.ps1 -ComposeFile docker-compose.review.yml -ResetPasswords
```

This operation:

- repairs role codes;
- replaces stale function, department, country, and facility grants;
- aligns administrator passwords with `secrets/review_preloaded_users.json` when `-ResetPasswords` is supplied;
- clears failed-login locks;
- revokes existing sessions so the next sign-in receives a fresh authorization matrix.

After completion, sign out fully and sign in again. Select the matching country for `tz.admin`, `ke.admin`, or `ng.admin`. `platform.admin` may use any of the three country selectors.

## Production repair

```powershell
.\scripts\repair-admin-access.ps1 -ComposeFile docker-compose.production.yml
```

Do not use `-ResetPasswords` in production unless the approved credential manifest is present and a controlled password reset is intended.
