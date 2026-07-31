# Real-Time Collaboration and Workflow Integrity — v10.7.0

## Exclusive patient-activity control

The application applies an exclusive lock to each selected patient and activity workspace. A user may work in the patient's chart while another user works in a different activity, but two users cannot edit the same patient activity simultaneously.

A lock is renewed by a heartbeat and expires five minutes after the last successful heartbeat. The lock holder is shown to other users without exposing unrelated clinical information.

## Permission-based handoff

A blocked user can request access and provide a reason. The current holder receives an in-application request and may:

- **Yes:** immediately close and transfer the patient activity to the requester.
- **No:** provide a mandatory reason and expected timeframe.

If the holder stops responding and the five-minute lock expires, the oldest pending requester receives the activity automatically. Every acquisition, request, response, denial, release and automatic transfer is audited.

## Workflow idempotency

Non-repeatable workflow processes are registered before execution. The database enforces a unique patient + encounter + workflow-code combination. Repeated arrival, registration completion, discharge, walk-in completion or patient-expiry initiation is rejected with a conflict response and the original workflow instance remains available in event history.

## AJAX refresh

Authenticated workspaces refresh through asynchronous API calls every 60 seconds. Refresh is deferred while:

- A modal workflow is open.
- The user is actively editing an input, textarea or selector.
- A clinical note contains unsaved text.
- The browser tab is hidden.

The same 60-second cycle checks incoming lock requests. Lock heartbeat renewal also occurs every 60 seconds.

## Hover-to-discover

Key navigation items, clinical actions and workflow controls expose concise contextual help on mouse hover or keyboard focus. Tooltips do not replace labels and do not contain protected health information.
