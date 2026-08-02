# Pakistan and Rwanda practice contexts — 10.16.2

Release 10.16.2 adds Pakistan (`PK`) and Rwanda (`RW`) as full authorization boundaries alongside Tanzania, Kenya and Nigeria.

## What a country context controls

- pre-authentication national/ministry identity;
- country and facility access grants;
- country-filtered facility and patient lookup;
- review-data identifiers, names, phone formats, addresses and coverage labels;
- local currency display and payment-channel choices;
- offline profile provenance and workspace flag ambience.

Selecting a country never grants access. Login still requires an active `COUNTRY` grant and at least one active `FACILITY` grant belonging to that country.

## Pakistan

- Formal context: Islamic Republic of Pakistan.
- Health authority: Ministry of National Health Services, Regulations and Coordination.
- Currency: PKR.
- Payment choices: cash, card, bank transfer, Raast, Easypaisa, JazzCash, 1LINK and configured crypto channels.
- The starter facility directory includes federally and provincially governed teaching hospitals sourced from the official Ministry, PIMS, Punjab health and Khyber Pakhtunkhwa health-system publications.

## Rwanda

- Formal context: Republic of Rwanda.
- Health authority: Ministry of Health.
- Currency: RWF.
- Payment choices: cash, card, bank transfer, MTN MoMo, Airtel Money, IremboPay and configured crypto channels.
- The starter facility directory uses the Rwanda Ministry of Health public hospital directory, including university, teaching, referral, specialized and district hospitals.

## Source references

- Pakistan Ministry of National Health Services, Regulations and Coordination: https://www.nhsrc.gov.pk/
- Pakistan Institute of Medical Sciences: https://pims.gov.pk/
- Government of Punjab Specialized Healthcare and Medical Education Department: https://health.punjab.gov.pk/
- Khyber Pakhtunkhwa Health Care Commission: https://hcc.kp.gov.pk/
- Rwanda Ministry of Health hospital directory: https://www.moh.gov.rw/affiliates-teaching-hospitals/hospitals

These starter directories are deployment reference data, not a claim of contractual participation by any facility. Production administrators should reconcile them with the approved national or institutional master-facility registry before go-live.
