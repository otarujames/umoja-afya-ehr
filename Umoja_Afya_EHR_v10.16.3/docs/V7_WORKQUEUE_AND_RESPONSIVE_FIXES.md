
# Release 7.0 Workqueue, Workflow-State and Responsive Workspace Corrections

Release 7.0 converts the Workqueue Management suggested actions from visual placeholders into backend-connected workflows. Open Queue, Reassign, Route, Defer, Complete, Resume/Reopen, Cancel, Create Task, View Rules and item-history review now operate on selected workqueue items and write audit events.

The Today's Patients workspace now derives the single next valid action from the appointment, encounter or walk-in state. Completed actions are no longer presented again. The supported progression is scheduled → arrived → registered → waiting triage → triaged → ready for provider → roomed → in progress → waiting results → ready for discharge → discharged.

The Today, Workqueue and ICT Administration workspaces use draggable splitters. Widths persist in local browser storage. Major cards also provide maximize/restore controls, and layouts collapse responsively on smaller screens.

The ICT access-matrix center pane now retains a usable minimum height with independent scrolling and a sticky audited-save region.
