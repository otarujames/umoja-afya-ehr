# Enterprise EHR Capability Map

Umoja Afya uses vendor-neutral module and workflow terminology.

| Capability domain | Umoja Afya implementation | Current release behavior |
|---|---|---|
| Identity and registration | National MPI, registration and consent | Search-before-create, duplicate review, emergency/unknown/newborn registration, coverage and proxies |
| Scheduling and referrals | Public duty-roster and private named-provider scheduling | Create, confirm, arrive, cancel, reinstate, no-show, reschedule and preserve status history |
| ADT and patient flow | Patient tracker and enterprise bed board | Arrival through discharge, transfers, occupancy, EVS and recent-discharge visibility |
| Ambulatory and inpatient record | Longitudinal chart and encounter record | Chart-linked notes, orders, results, medications, flowsheets and follow-up |
| Clinical documentation | Note composer and signature workflow | Draft, assisted draft, sign, cosign and legal-record safeguards |
| Orders and results | CPOE and diagnostic result management | Create, hold, resume, cancel, reinstate and acknowledge critical results |
| Nursing and eMAR | Nursing workspace and timed flowsheets | Start, pause, resume, change, stop, observations and medication administration |
| Medication management | Ordering, verification and administration | Pharmacy verification, dose administration history and inventory linkage |
| Laboratory and blood bank | Ancillary work queues | Specimen/result workflow foundation, critical-result linkage and transfusion activities |
| Radiology and imaging | Imaging work queues and PACS integration points | Protocol, status, report and critical-finding activities |
| Perioperative care | Theatre and anesthesia workspaces | Readiness, procedure, device/medication and recovery activities |
| Specialty care | Maternity, cardiology, orthopaedics/trauma, oncology, critical care and rehabilitation | Record-linked configurable activities and specialty flowsheets |
| Revenue cycle | Charges, claims, payments and denials | Persistent transaction states and reconciliation work queues |
| Supply chain | Inventory and asset control | Receipt, issue, transfer, adjustment, waste, batch and expiry |
| Quality and public health | Safety incidents, registries and surveillance | Audited events and national interface outbox |
| Analytics and M&E | Aggregate enterprise summaries | Operational, clinical, financial and programme indicators without unrestricted chart display |
| User administration | Per-user functional access matrix | Functions, departments and facilities assigned independently and audited |
| Interoperability | FHIR R4, HL7 v2, DICOM and integration outbox | Starter APIs and feature-gated national/facility adapters |
| Remote care | Patient-record-linked telehealth | Schedule, start, pause, resume, complete and cancel |

Patient-facing portal and mobile delivery are not part of Release 10.7.0.
