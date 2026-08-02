# Release 10.16 Smart CPOE

The Orders workspace is now a patient- and encounter-controlled computerized provider order entry experience. It uses familiar enterprise EHR interaction patterns—live lookup, favorites, recent orders, adaptive detail forms, order panels, a signing basket and a final review—but it does not copy any vendor's proprietary interface, content or assets.

## Clinician workflow

1. Open the intended patient record and select an active encounter.
2. Find an approved orderable by any part of its name, code, synonym, category or subcategory. Search tokens progressively narrow and rank results.
3. Complete the context-sensitive composer. Medication orders require dose, route and frequency. Laboratory, blood-bank, imaging, consult, nursing, ADT and operational orders expose their relevant fields.
4. Add individual orders or a governed order panel to the basket.
5. Review patient, encounter, allergies, medications, indication, dose, priority and routing.
6. Sign the basket once. The server validates and commits the batch atomically, so it cannot leave a partially signed panel.

Historical encounters are review-only. The API rejects new orders for discharged, transferred or left-without-being-seen encounters even if a browser request is manipulated.

## Catalog and starter content

The release includes 1,095 starter orderables across clinical and non-clinical categories. It is an extensible reference catalog, not a claim that one static package can contain every locally licensed medicine, laboratory test, device, workflow or service in every healthcare system.

Eight versioned starter panels contain 49 governed items:

- Emergency sepsis — initial bundle
- Emergency chest pain
- Acute stroke — initial pathway
- Adult inpatient admission
- Diabetes follow-up
- Antenatal initial assessment
- Postoperative ward care
- Discharge readiness and follow-up

Starter content is a workflow aid, not autonomous medical advice. Clinicians must review every selected item, and local clinical governance must reconcile content with the facility formulary, laboratory directory, radiology protocols, national guidance and scope-of-practice rules.

## Configuration administration

Only an authenticated administrator with `system.configuration.manage` can:

- create a custom approved orderable;
- supply synonyms, routing, specimen/route, defaults and safety requirements;
- save the current basket as a local governed order panel.

Creation records the administrator, governance reason, version, approval time and audit event. Ordinary ordering users may search and use active catalog content but cannot author it.

## Data and audit model

- Each order stores its catalog code, patient encounter, structured details JSON, indication, instructions, priority, signer and timestamp.
- Each order creates an immutable status event and managed event.
- Course changes remain hold, resume, cancel and reinstate events; the original order is not deleted.
- Order sets have stable codes, versions, approval provenance, encounter applicability and ordered child items.
- Medication details are validated again by the API, not only by the browser.

## Deployment

Alembic revision `6a7b8c9d0e1f` adds structured order fields, order-set tables and starter-set migration for existing catalogs. Production prestart runs migrations before the application serves traffic.

After deployment, verify:

```bash
cd /opt/umoja-afya-ehr
docker compose exec app python -m alembic current
docker compose exec app python scripts/check_migrations.py
docker compose ps
```

Then test one laboratory order, one medication order with dose/route/frequency, one operational order, one starter panel, and a hold/resume cycle in a non-production patient record.
