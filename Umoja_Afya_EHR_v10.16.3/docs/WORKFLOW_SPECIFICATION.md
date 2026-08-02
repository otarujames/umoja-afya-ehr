# Core Workflow Specification

## 1. Patient Registration registration

The registration workflow is designed around search-before-create:

1. Search by national MPI ID, MRN, NIDA number, name, date of birth or phone.
2. Review possible duplicate identities.
3. Select an existing identity or explicitly override creation with a reason-controlled workflow.
4. Capture demographics, address, next of kin, payer, member number and encounter details.
5. Record consent, guardian/proxy or emergency legal basis.
6. Create pre-registration, standard, emergency, unknown-patient or newborn encounter.
7. Place the encounter into the active patient-flow tracker.
8. Write an auditable registration event.

## 2. Provider patient tracker

The tracker provides six operational columns:

- Arrived / Registration
- Waiting for Triage
- Triaged / Ready
- Roomed
- In Progress / Waiting Results
- Ready for Discharge

Each patient card displays identity, service, location, acuity and elapsed waiting time. Quick actions move the encounter to the next controlled state. The recently discharged list is separated from active work while remaining one click away.

## 3. Flowsheets

A flowsheet has a patient, optional encounter, clinical template, cadence, parameter list, owner, timer, observations and event history.

Supported controls:

- **Start:** activates a draft and starts elapsed-time calculation.
- **Pause:** stops active time while preserving accumulated duration.
- **Resume:** restarts active timing.
- **Change:** changes cadence, name or parameters with a reason.
- **Stop:** closes the sheet and prevents new observations.

Observation entries capture parameter, value, unit, source, recorder and timestamp. Every control and observation creates an audit event.

## 4. Orders and results

Providers can place laboratory, imaging, medication, blood, procedure and referral orders against an encounter. Results can be listed by patient and criticality. Critical results remain actionable until acknowledgement is recorded with user and timestamp.

## 5. Discharge and transition of care

The discharge workflow captures disposition, summary and follow-up. Completing discharge removes the patient from the active tracker and places the encounter in Recent Discharges. The chart retains the summary, follow-up and facility context.
