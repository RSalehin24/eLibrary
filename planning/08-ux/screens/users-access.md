# Users and access

Status: DRAFT

**Purpose**: the administrator manages invitations, accounts, roles and per-user grants in one place.
**Primary action**: Invite (list); Add grant (user detail).
**Routes**: `/admin/users`, `/admin/users/:id` (Audit is the third tab, [audit](audit.md)). **Auth**: `manage_users`, session that completed TOTP where required. **Service owner**: identity. **Requirements**: REQ-WEB-018; REQ-IDN-009..012, 018, 020, 031, 033. Flow: [grant management](../flows/grant-management.md).

## Data

`GET/POST /users`, `GET/PATCH /users/{id}`, `POST /users/{id}/resend-invite`, `PUT /users/{id}/status`, `PUT /users/{id}/role`, `DELETE /users/{id}`, `GET/POST /grants`, `POST /grants/batch`, `PATCH/DELETE /grants/{id}`, `POST /users/{id}/read-once/{book_id}/reset` ([identity contract](../../07-contracts/http/identity.md)).

## Content

- **List**: search, status filter (invited, active, suspended, disabled), role filter, keyset load more; row shows name, email, role chip, status chip, TOTP state. Invite dialog: email, display name, role (reader, operator, admin), language; the account is created `invited` and a failed mail does not undo it (shown as "Invite created, mail not sent yet, Resend").
- **User detail** (drawer on expanded and large, sheet on medium, full screen on compact): profile and status; actions Resend invite, Suspend, Reactivate, Disable (confirm), Change role (confirm), Delete account (confirm naming the user, explains that their reading data is erased); the **Grants** table: scope, book (or all), expiry, granted by, reason, active; Add grant, edit expiry, revoke (confirm); read-once counter reset per book.
- Role defaults (reader: browse, preview, read, kindle; operator and admin per D-45) are shown read-only above the grants so "what can this user do" is one view; `download` and `read_once` appear only as explicit grants.
- **Add grant** dialog: choose several scopes and optionally one book and expiry and a required reason; submitted as one batched atomic request so either all apply or none (REQ-WEB-018). It uses `POST /grants/batch` (D-54).
- Self-protection: no self-grant, no change to one's own role or status, no demoting or removing the last admin; these controls are disabled with the reason, and the server enforces it (`forbidden`). Admin lock-out recovery is a host command, not a UI feature (D-38).

## States

| State | Behaviour |
|---|---|
| Loading | skeleton rows |
| Empty | list: "No users match" (a fresh system always has the first admin); grants: "No explicit grants, this user has the role defaults" |
| Ready | list and detail |
| Error | banner with Retry; `email_taken`, `duplicate_grant`, `invalid_transition`, `stale_revision` as inline messages |
| Forbidden | no `manage_users`: nav absent, route shows forbidden; 403 `mfa_required` goes to TOTP |
| NotFound | user deleted meanwhile |
| Offline | banner; mutations disabled with reason |

## Layout

compact: list of cards, detail full screen, bottom bar nav; medium: table plus detail sheet; expanded: table with right drawer; large: wider drawer with grants beside the profile.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.users.title` | Users and access | ব্যবহারকারী ও অনুমতি |
| `ux.users.invite` | Invite | আমন্ত্রণ জানান |
| `ux.users.resend` | Resend invite | আমন্ত্রণ আবার পাঠান |
| `ux.users.suspend` | Suspend | স্থগিত করুন |
| `ux.users.disable` | Disable | নিষ্ক্রিয় করুন |
| `ux.users.grants` | Grants | অনুমতি |
| `ux.users.grant.add` | Add grant | অনুমতি যোগ করুন |
| `ux.users.grant.revoke.confirm` | Revoke {scope} for {name}? | {name}-এর {scope} অনুমতি বাতিল করবেন? |
| `ux.users.delete.confirm` | Delete {name} and their reading data? | {name} ও তাঁর পড়ার তথ্য মুছে ফেলবেন? |
| `ux.users.self` | You cannot change your own access | নিজের অনুমতি আপনি বদলাতে পারবেন না |

Analytics: none. Accessibility: table and drawer with focus return to the row; destructive confirm dialogs name the user; status and role are text chips; disabled controls expose their reason.

## Open

C-1 (who reads the audit log), O-1 (`user.deleted` event).
