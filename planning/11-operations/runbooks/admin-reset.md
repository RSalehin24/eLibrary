# Runbook: admin reset (locked-out admin)

Status: DRAFT

Decision D-38: recovery is a documented **host command** of identity, `admin-reset`. There is no break-glass account, no hidden credential, no HTTP route and no two-person approval (REQ-IDN-033, INV-IDN-033). Admins still cannot change themselves or remove the last admin through the app.

**Symptoms.** The only admin lost the password or TOTP device; or no admin can sign in.

**Impact.** No user administration; the rest of the library works.

**Quick check.** Confirm identity is healthy (`/internal/ready`) and that sign-in fails for the account, not the service. Check for lockout throttle only (it expires).

**Fix** (needs shell access to the host and permission to run containers):
1. Identify the admin account by its email. Verify the requester out of band (the owner, in person or by a trusted channel); the command cannot verify identity.
2. Run `admin-reset` in the identity container as a **dry run** (default). Read the plan: target account, what is cleared (sessions revoked, TOTP reset when requested), the one-time setup link to be created.
3. Run it again with the explicit apply flag. It sets a one-time setup link and **never a password**; the link is shown once on the host terminal, not logged or mailed.
4. The admin opens the link, sets a new password and re-enrols TOTP.

**Verify.** The admin signs in with TOTP; the audit log holds the `admin-reset` run with host user and time (every run is audited); old sessions are gone.

**Follow-up.** Tell the owner; if the cause was a lost device keep the audit entry; if compromise is suspected also run [key-compromise](key-compromise.md). If no admin exists at all (empty identity), use `seed-first-admin` as in [launch](launch.md) step 2; it refuses when an admin exists.
