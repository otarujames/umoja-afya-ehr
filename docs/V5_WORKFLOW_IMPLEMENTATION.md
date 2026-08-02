# Release 5.0 Workflow Implementation Map

| Requested correction | Implemented behavior |
|---|---|
| Order lookup | Searchable 1,094-item clinical and non-clinical order catalogue; patient/encounter composer; course changes and history. |
| Automatic MRN | Facility-prefix MRN generated transactionally on registration; MRN input is read-only. |
| Patient Station / Registration overlap | Patient Station uses a fixed three-region layout; Registration/ADT uses four focused in-page workspaces. |
| Messages | Functional inbox, sent, archived, compose, read/unread and archive actions. |
| IT-friendly settings | User × function × department × facility checkbox matrix with audit reason and account controls. |
| Record/chart-driven pages | Orders, results, notes, flowsheets, medications and specialties are locked until a chart is selected. |
| Bed Board | Facility and unit selection precede loading beds; no hospital-wide patient wall. |
| Tanzania facilities | 45 review contexts plus audited bulk import of an approved HFR master export, grouped in Change Context. |
| Patient expiry | Death/expiry workflow, encounter closure, mortuary/HIM task, certificate data and reversible event history. |
| Event / ED / specialty workflows | Managed-event ledger with authorized undo; ED track board; specialty pathway configurations. |
| Inpatient flowsheets | Spreadsheet time columns, 10 templates, 207 variables, 72 device-capable variables and device ingestion APIs. |

## Record-context rule

Operational dashboards may show aggregate counts and minimal worklist identifiers. Full clinical data is loaded only after an explicit patient selection or from a record-linked workflow item.

## Event correction rule

Cancel, undo, reinstate and reopen actions do not delete prior records. The system records the original state, new state, actor, reason, timestamp, related patient/encounter and reversal relationship.
