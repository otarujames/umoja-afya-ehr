# Umoja Afya EHR 10.14.0

## Record-centred Patient Station

- Replaced the duplicated Today's Patients and workqueue panels with a longitudinal Record Finder.
- Added an always-visible storyboard showing the selected patient, current activity and optional encounter.
- Added direct registration-side and chart-side access from the selected record.
- Added guarded scheduled-arrival, walk-in and triage workflows.
- Added record-only phone call, refill and financial-counseling activities that do not manufacture encounters.
- Connected Print Forms to the existing audited label, wristband, facesheet and document preview workflow.

## Notes, flowsheets and financial workflow

- Signed notes now display a visible user-and-time event trail; signed content remains immutable and corrections use addenda.
- Flowsheet names, cadence and variable lists can be changed with a required audit event while existing observations remain intact.
- Billing is scoped to the selected patient and active encounter, including billed-to responsibility and claims.
- Added patient financial counseling, payment plans and payment collection.
- Currency follows the active country (TZS, KES, NGN, PKR or RWF), with country-specific mobile money plus cash, card, bank and crypto transaction references.
- The API rejects charges, claims, payments, activities and flowsheets when the supplied encounter belongs to a different patient.

## VPS deployment

For a host with an existing Traefik Docker provider and external network:

```sh
cd /opt/umoja-afya-ehr
docker network inspect "${TRAEFIK_NETWORK:-traefik}" >/dev/null
docker compose -f docker-compose.production.yml -f docker-compose.traefik.yml config --quiet
docker compose -f docker-compose.production.yml -f docker-compose.traefik.yml up -d --build --remove-orphans
```

Set `UMOJA_PUBLIC_HOST`, `UMOJA_CORS_ORIGINS`, `UMOJA_ALLOWED_HOSTS`, `TRAEFIK_NETWORK`, and (if different) `TRAEFIK_CERTRESOLVER` in `.env`. The overlay disables the bundled host-port nginx service, preventing port 80/443 conflicts with Traefik.
