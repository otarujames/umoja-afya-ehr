# User Administration Guide

## Access design

Each user account stores three independent checkbox sets:

- **Functions:** actions and workspaces the user can operate
- **Departments:** organizational areas in which the user works
- **Facilities:** institutions whose records and workflows the user may access

Access templates preselect common combinations. Templates do not override the final checkbox matrix and do not become hard role silos.

## Create a user

1. Sign in with an account assigned `system.users.manage`.
2. Open **System Admin & Security**.
3. Select **Add User**.
4. Enter a unique username and display name.
5. Select an optional template or start with **Custom**.
6. Select at least one function, department and facility.
7. Enter or generate a strong temporary password.
8. Record the provisioning reason.
9. Select **Create User**.
10. Copy the username and temporary password from the confirmation screen.
11. Sign out and test the new account.

The backend validates username format, uniqueness, password strength, facility existence and all function/department codes before committing the account.

## Edit a matrix

Select **Edit matrix** beside the account. Add or remove individual functions, departments or facilities and enter a reason. The prior and updated matrices are written to the audit log.

## Account actions

- **Disable/Enable:** changes whether the account can authenticate.
- **Password:** replaces the local password with a new strong temporary password.
- **Unlock API:** restores an active account through the audited unlock endpoint.

## Cross-functional IT example

An IT analyst may be assigned:

- `system.users.manage`
- `system.interfaces.manage`
- `system.audit.view`
- `analytics.view`
- Departments: ICT, HIM and Public Health/M&E
- Facilities: MNH Upanga, MNH Mloganzila, MOI, JKCI and ORCI

The functions are assigned individually. The user does not need an all-powerful administrator profile.

## Production requirements

Local passwords are provided for development and controlled pilot use. Production should use government identity management, MFA, joiner/mover/leaver automation, periodic access review, emergency-access controls and privileged-access monitoring.
