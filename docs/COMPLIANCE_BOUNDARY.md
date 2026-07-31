# Compliance and Certification Boundary

## Release status

Umoja Afya Enterprise EHR 10.7.0 is an engineering and controlled-review release with technical and documentary controls designed to support a deploying organization's HIPAA Security Rule, SOC 2, ISO/IEC 27001, ISO/IEC 27701, ISO 27799 and ISO 22301 programmes.

The software package itself is **not** a legal determination of HIPAA compliance, a SOC 2 report, or an ISO certificate. Those outcomes depend on the complete operating organization, including governance, policies, workforce practices, contracts, facilities, cloud/data-centre configuration, risk management, evidence over time and independent assessment.

## Included technical controls

- Unique user accounts, Argon2id password hashing, failed-login lockout and revocable sessions.
- Per-user function × department × facility access matrices.
- Patient-context boundaries for clinical workflows.
- Time-limited, reason-coded and audited emergency access.
- Security headers, request limits, rate limiting and production TLS profile.
- Tamper-evident application audit records and workflow histories.
- Controlled course changes for appointments, encounters, orders and workqueue items.
- PostgreSQL production profile, Alembic migrations, backup/restore scripts and health checks.
- Synthetic-only Docker review data.

## Required before live patient use

1. Complete enterprise risk analysis and data-protection impact assessment.
2. Approve policies for access, privacy, retention, incident response, business continuity, change control and vendors.
3. Configure Government identity provider, MFA, certificates, encryption keys and secrets management.
4. Validate all clinical workflows, content, advisories, order sets and interfaces.
5. Perform vulnerability scanning, software-composition analysis and independent penetration testing.
6. Execute migration validation, disaster-recovery testing and operational acceptance.
7. Establish a Business Associate / processor contracting model where applicable.
8. Collect operational evidence for the required SOC 2 review period.
9. Implement an organizational ISMS/PIMS and complete accredited ISO certification audits where certification is desired.
10. Obtain formal clinical-safety and Ministry go-live authorization.
