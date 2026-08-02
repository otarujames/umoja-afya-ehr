# Security, Privacy and Clinical Safety Baseline

## Required controls

- Government-controlled Tanzanian production hosting and encryption keys.
- TLS in transit and encryption at rest.
- Multi-factor authentication for privileged and remote access.
- Role-, relationship-, location-, facility- and purpose-based access.
- Sensitive-record segmentation and VIP controls.
- Reason-coded, time-limited break-glass access.
- Tamper-evident audit events and routine access review.
- Endpoint management, network segmentation, vulnerability management and incident response.
- Data minimization, retention schedules, legal hold and controlled destruction.
- Data-protection impact assessment for high-risk processing.
- Controlled cross-border support and transfer authorization.

## Clinical safety

- No autonomous diagnosis or prescribing.
- High-risk alerts require evidence ownership, validation, monitoring and rollback.
- Medical-device interfaces require verification and reconciliation.
- Critical results require accountable acknowledgement.
- Downtime and recovery workflows require scheduled simulation.
- Clinical content and order sets require multidisciplinary governance.

The demo role selector is not authentication. Replace it with a government identity provider using OpenID Connect or an approved equivalent before any real-data use.
