# Release 9.0 — Clinical Notes and Unit Manager Upgrade

## Clinical Documentation Studio

Clinical documentation is record-driven. The route will not display clinical notes until a patient and active encounter are selected.

The page is divided into three independently scrollable and resizable panes:

1. **Note navigator** — search, status and note-type filters; draft/signed indicators; author, service and time context.
2. **Composer or legal-note viewer** — templates, smart phrases, encounter selection, note title/type, service, cosign flag and the clinical narrative.
3. **Clinical guardrails** — draft/signed/cosign counts, patient-specific practice advisories and legal-record integrity guidance.

### Built-in note templates

- Progress Note
- History and Physical
- ED Provider Note
- Nursing Shift Note
- Procedure Note
- Consult Note
- Discharge Summary
- Death Pronouncement Note

### Documentation lifecycle

- **Create Draft** links the note to the selected patient and encounter.
- **Edit Draft** is permitted while the note remains unsigned; each update creates an event and audit record.
- **Sign** locks the note in the legal record with signer, timestamp and attestation.
- **Add Addendum** is the correction path for a signed note. The original text remains preserved and the addendum is appended with author, reason and timestamp.
- **History** displays create, edit, sign and addendum events.

The system rejects direct updates to signed notes with HTTP 409. It does not delete or silently replace the original clinical narrative.

## Unit-first Capacity Management

The former hospital-wide bed-board behavior is removed. Opening Unit Manager presents a unit lookup first. Patient identities and bed/care-space details remain hidden until the user selects a unit.

### Context sequence

1. Select hospital/campus through Change Context.
2. Search or filter the unit catalogue.
3. Select the unit.
4. Load only that unit's room and bed/care-space layout.
5. Perform assignment, occupancy, movement, discharge/vacate and turnover actions.

### Care-setting categories

- Emergency / ED
- Critical Care
- Women & Children
- Surgical & Procedural
- Procedural / Day Care
- Isolation
- Mental Health
- Inpatient

ED/ER units use **care spaces** as the operational term. Examples include Emergency Observation Unit and Emergency Resuscitation Unit. Their command pane links directly to the ED/ER Tracking Board.

### Unit dashboard

The selected-unit response provides:

- capacity and current-status totals;
- beds, bays or care spaces grouped by room;
- available, assigned, occupied, dirty, cleaning and blocked states;
- linked patient and encounter summaries where applicable;
- isolation and bed-type information;
- pending placement or movement;
- occupancy and turnover indicators.

All bed-state changes continue through the existing audited action endpoint. Invalid transitions are rejected rather than visually simulated.

## Usability and accessibility

- Draggable pane splitters retain local layout preferences.
- Independent pane scrolling prevents table and panel overlap.
- Responsive breakpoints stack panes on smaller screens.
- Strong keyboard focus states support non-mouse operation.
- Reduced-motion preferences disable animation.
- Subtle transitions and status-specific visual cues improve discoverability while maintaining a clinical interface.

## Compliance and safety boundary

The upgrade reinforces record context, signed-note immutability, addendum-based corrections, actor/timestamp provenance, minimum-necessary unit views and audited bed-state transitions. These are technical controls supporting privacy, security and assurance readiness. They do not independently establish HIPAA compliance, SOC 2 attestation or ISO certification; the deploying organization must operate the corresponding administrative, physical and governance controls.
