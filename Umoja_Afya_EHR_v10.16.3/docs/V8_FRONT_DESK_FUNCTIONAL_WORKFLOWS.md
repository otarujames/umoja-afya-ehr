# Release 8.0 — Front-Desk Functional Workflow Corrections

## Today’s Patients filtering

The worklist filter state is applied to the currently selected date/worklist before rendering. The same filtered collection drives:

- the patient table;
- Expected;
- Arrived;
- Checked In;
- Waiting;
- Ready;
- Completed;
- the visible/total result summary.

Search matches patient name, MRN, MPI, phone, service, queue, status and on-duty team. Service, queue and status can be combined. Pressing Enter in the search field performs the same action as **Apply**. **Clear** restores the complete worklist.

Yesterday, Today and Tomorrow are queried independently by date. Walk-Ins uses the active walk-in operational feed.

## State-aware patient flow

The next action is calculated from the current appointment, encounter or walk-in state. The interface does not offer an already-completed step again. Backend transition guards remain authoritative and every change is audited.

## Patient Print Center

**Print Forms & Labels** opens a record-linked print center containing:

- patient identification label;
- encounter/visit label;
- chart folder/spine label;
- specimen collection label;
- adult wristband;
- paediatric wristband;
- newborn mother–baby wristband;
- patient facesheet;
- registration and consent summary;
- encounter summary;
- referral cover sheet;
- discharge transition facesheet.

Users select one or more templates, copies, language and printer/output. The backend creates persistent `print_job` records and writes an audit event. Browser printing supports physical printing or Save as PDF during Docker review.

## Benefit verification

The selected patient’s payer, membership number and service are loaded into the verification form. Results are saved in `coverage_verification`.

- Valid scheme plus member number returns a simulated **Eligible** result for Docker review.
- Cash/self-pay is routed through the self-pay path.
- Missing membership information returns **Needs Review** and creates an item in the NHIF eligibility workqueue.

The screen displays prior verification history.

## Travel and communicable-disease screening

The screening form captures recent travel, outbreak-area exposure, infectious contact, fever, cough, breathing difficulty, rash, diarrhoea/vomiting, unexplained bleeding and narrative notes.

The backend assigns Low, Moderate or High risk and persists the assessment in `travel_screening`. Moderate and High results generate front-desk arrival-exception workqueue items with appropriate priority.

## Persistence and audit

Release 8 adds three tables:

- `print_job`;
- `coverage_verification`;
- `travel_screening`.

All three workflows record patient context, encounter context where available, actor, timestamps and audit events.
