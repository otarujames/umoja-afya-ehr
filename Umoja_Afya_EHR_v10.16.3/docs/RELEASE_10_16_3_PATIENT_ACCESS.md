# Umoja Afya EHR 10.16.3 — Patient Access and Rooming

## Front-desk workflow

Today’s Patients keeps the selected record and its next valid action in a persistent action dock above the scrolling table. The table’s action column remains visible while horizontally scrolling. On-duty teams and service points have moved to an expandable operations drawer below the working area, preserving access without consuming a permanent third column.

## Encounter-controlled triage and rooming

Rooming remains part of the selected physical encounter:

1. `WAITING_TRIAGE` moves to `TRIAGED` after the triage assessment is saved.
2. The triage user may keep the patient in the completed-triage queue or place the patient immediately.
3. Placement moves the same encounter through `READY_FOR_PROVIDER` to `ROOMED` and records the room, user, timestamp and audit activity.
4. The default room is `General Practice Room`; authorized staff may change it to the hospital’s real room or care space.
5. `ROOMED` records placement only. Provider time begins when the encounter explicitly moves to `IN_PROGRESS`.

Patient Care displays completed-triage and roomed patients in separate lists. Each button retains the patient and encounter identifiers so triage, rooming and provider documentation cannot silently attach to a different visit.

## Recent patient records

Patient Station and the enterprise patient lookup show recently viewed records. This convenience list is scoped to the authenticated user, selected country and selected facility. It contains compact identity/search metadata only; clinical note bodies are not written into this browser preference list.

## Refresh and locking

Routine AJAX refresh for notifications, message counts and workspace data runs every five minutes. Manual Refresh controls remain available. The exclusive clinical activity-lock heartbeat remains at one minute because it protects against two users editing the same activity; it is intentionally not relaxed to five minutes.

## Deployment

The release uses the existing PostgreSQL schema and Alembic migration chain. Rebuild the application image so the frontend and tracker route changes are included, then run the standard preflight and migration commands before replacing the running container.
