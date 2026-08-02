# Patient Station, Recents and Favorites — 10.4.0

## Activity launcher

The activity launcher now maintains user-scoped Pinned and Recent activity lists. Activities can be pinned or unpinned with the star control. The recent list is updated whenever a workspace is opened and is limited to the ten most recent activities.

## Patient lookup

Patient Search & MPI is now presented as a Patient Station-style three-pane workspace:

1. Favorites and recently opened patient records.
2. Enterprise MPI search results.
3. Patient preview and record-context actions.

Opening a patient from search or memory establishes patient context before launching Patient Station, Chart, Event History or encounter workflows. Favorite and recent-patient memory is scoped to the authenticated username and does not modify the legal health record.

## Privacy behavior

The browser memory stores only the minimum identity fields needed to re-identify a recently opened patient in the authorized EHR session. It is separated by authenticated username. Production deployments should continue to enforce automatic session lock, managed-device controls, browser-data clearing policies and workstation privacy protections.
