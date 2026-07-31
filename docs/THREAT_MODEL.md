# Threat Model

## Protected assets

Patient identity, clinical records, orders/results, medication data, claims, credentials, audit records, integrations, encryption keys and availability of clinical workflows.

## Principal threats and controls

| Threat | Primary controls |
|---|---|
| Credential theft | MFA production requirement, Argon2id, lockout, revocable sessions, TLS |
| Excessive internal access | Function/department/facility matrix, patient context, access reviews, audit |
| Emergency-access abuse | Reason, duration, identity, patient and review record |
| Record tampering | Signed notes, immutable event histories, audit, database constraints, backup |
| API abuse | Authentication/RBAC, request-size limits, rate limiting, validation, private DB |
| Ransomware/destructive action | Segmentation, least privilege, immutable/offline backups, restore exercises |
| Integration compromise | API gateway, certificates, interface allowlists, payload validation, outbox audit |
| Data exfiltration | Minimum necessary access, restricted exports, TLS, logging and anomaly review |
| Clinical automation error | Human review, no autonomous diagnosis/prescribing, rule ownership and rollback |
| Service outage | Health checks, recovery objectives, downtime procedures and failover planning |

Risk acceptance and residual-risk decisions must be approved by the deploying organization's accountable leadership.
