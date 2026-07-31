# Multi-Country Practice Context — v10.5.0

## Pre-login country selection

The public landing page requires selection of Tanzania, Kenya, or Nigeria before authentication. No hospital directory is exposed before sign-in. The selected country controls ministry branding and is submitted as part of the authentication request.

## Country access matrix

ICT Administration now includes an independent Countries matrix in addition to Functions, Departments, and Facilities. A successful username/password verification does not authorize a country automatically. The authentication service verifies that the selected country is present in the user's active COUNTRY grants and that the user has at least one facility grant in that country.

Denied cross-country attempts return HTTP 403 and create a COUNTRY_LOGIN_DENIED audit event.

## Post-login context

Change Context and the facility selector show only facilities that satisfy both conditions:

1. The facility belongs to the active country.
2. The facility is assigned to the authenticated user.

Country selection therefore does not grant access by itself.

## Country-specific review data

The review seed includes:

- Tanzania facilities and Tanzanian synthetic patients.
- Kenya national, referral, private, and faith-based facilities with Kenyan synthetic names, +254 phone formats, SHA coverage labels, and KE identifiers.
- Nigeria federal, state, private, and specialist facilities with Nigerian synthetic names, +234 phone formats, NHIA coverage labels, and NG identifiers.

All review records are synthetic and must not be used as real patient information.
