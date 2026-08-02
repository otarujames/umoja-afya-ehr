# Production Readiness Checklist

## Governance and clinical safety

- [ ] Ministry executive sponsor and product office designated
- [ ] MNH/MOI/JKCI/ORCI workflow owners approve configured workflows
- [ ] Clinical Safety Officer appointed
- [ ] Hazard log and clinical safety case approved
- [ ] Medication, order-set, alert and terminology governance established
- [ ] Downtime, mass-casualty and cyber-incident procedures rehearsed

## Privacy and legal controls

- [ ] Data Protection Impact Assessment completed
- [ ] Data-controller and processor responsibilities documented
- [ ] Patient notice, proxy, correction, complaint and disclosure-accounting workflows approved
- [ ] Break-glass policy, sensitive-data segmentation and VIP controls validated
- [ ] Tanzania data residency and cross-border support controls approved

## Technology

- [ ] Production PostgreSQL HA cluster deployed in approved Tanzania infrastructure
- [ ] Point-in-time recovery and encrypted backups tested
- [ ] First administrator created through token-protected setup; bootstrap token deleted or rotated
- [ ] Government SSO and MFA enabled; local emergency administrator restricted; no demonstration accounts present
- [ ] API RBAC, treatment relationship, facility scope, sensitive-record segmentation and break-glass controls validated
- [ ] TLS certificates and network segmentation installed
- [ ] SOC monitoring, endpoint protection, vulnerability management and incident response operational
- [ ] Alembic migration executed and independently reviewed
- [ ] Load, failover, recovery, penetration and secure-code testing passed

## Interfaces

- [ ] NIDA identity verification approved and tested
- [ ] NHIF/UHI eligibility, authorization and claims certified
- [ ] GePG payment reconciliation certified
- [ ] DHIS2/eIDSR reporting accepted
- [ ] eLMIS/MSD stock interfaces certified
- [ ] HL7 v2, FHIR R4, DICOM, analyzer and medical-device interfaces validated
- [ ] Interface replay, reconciliation and monitoring procedures approved

## Data migration

- [ ] Source systems inventoried
- [ ] MPI matching, duplicate resolution and merge policy approved
- [ ] Data mapping and terminology crosswalks validated
- [ ] Trial migrations reconciled
- [ ] Legal retention and legacy read-only access plan approved

## People and operations

- [ ] Role-based training and competency validation complete
- [ ] Super-user, service desk, command centre and escalation coverage staffed
- [ ] Go-live readiness score accepted
- [ ] Go-live support and stabilization plan approved
- [ ] Post-go-live optimization and benefits measurement scheduled
