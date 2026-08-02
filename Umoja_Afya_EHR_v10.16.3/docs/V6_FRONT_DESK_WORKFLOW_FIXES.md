# Release 6.0 Front-Desk and Walk-In Corrections

## Today’s Patients

The front-desk workspace now queries real backend records for Yesterday, Today, Tomorrow and Walk-Ins. Search, service, queue and status filters operate on the loaded record set. The page uses three independent panes: patient worklist, selected-patient workflow, and roster/context. Each pane owns its scrolling region to prevent table and card overlap.

## Integrated walk-in workflow

The walk-in flow no longer redirects to Patient Station. It remains in one modal and advances through:

1. Search or create patient
2. Demographics
3. Coverage and consent
4. Encounter
5. Arrival, service point and route

New patients receive an automatically assigned facility MRN. The final action registers the patient, reuses the newly created encounter, records arrival, creates a walk-in episode, publishes the one-second arrival notification and creates the registration follow-up workqueue item.

## Context and units

The page exposes Change Hospital / Unit and Unit Manager actions. Context selection is sourced from the Tanzania government facility context tree. Changing facility reloads patient lists, service points and rosters. Unit Manager remains unit-first rather than presenting all beds across the hospital.

## Flowsheets

Flowsheets remain spreadsheet-style inside the chart. Adult inpatient content now explicitly includes bathing/bed bath, oral care, linen change, bed and environmental safety assessment, comprehensive intake/output and expanded wound assessment and wound-care documentation.

## Login

The Tanzania Government coat of arms is displayed on the login page above the Umoja Afya identity.
