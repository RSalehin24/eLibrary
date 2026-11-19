# Profile and settings

Status: DRAFT

**Purpose**: the signed-in user's own preferences and security: theme, language, profile and image, password, TOTP, Kindle addresses and a data export.
**Primary action**: Save (per section).
**Routes**: `/settings`, `/settings/profile`, `/settings/appearance`, `/settings/security`, `/settings/kindle`, `/settings/data`. **Auth**: signed in (Kindle section: `kindle`). **Service owner**: identity (reader preferences and export: reader; catalog export: catalog; theme: web). **Requirements**: REQ-WEB-007, 019; REQ-IDN-004, 006, 028, 034; REQ-RDR-017.

## Sections

| Section | Content | API |
|---|---|---|
| Profile | display name, email (read only), profile image upload, replace and remove | `GET/PATCH /me`, `PUT/DELETE /me/profile-image` |
| Appearance | theme System, Light, Dark (button toggle, persisted, applied before first paint); UI language Bengali, English; link to reader display settings, which are edited inside the reader | web cookie and local storage; `PATCH /me` for language |
| Security | change password (current password, new password, code when TOTP is on; other sessions are signed out); TOTP status; **TOTP stepper dialog**: 1 scan QR or copy secret, 2 enter a code, 3 done; Disable and Reveal secret require re-authentication (password and code); a TOTP-required account cannot disable it and the control says why | `POST /me/password`, `GET /me/totp`, `/me/totp/setup`, `/confirm`, `/disable`, `/reveal` |
| Kindle | up to 5 validated addresses, add, edit, remove; the sender address and the "approve the sender in your Amazon account" instruction | `GET/PUT /me/kindle-addresses` |
| Data | Export my data (one JSON download bundling the identity, reader and catalog exports, D-55); account deletion is on request to an administrator, stated in text | `GET /me/export` (identity), `GET /me/export` (reader), `GET /me/export` (catalog: shelf and saved filters) |

The profile image is validated by the server by bytes (allow-listed types, SVG refused, size limit from [limits](../../04-architecture/cross-cutting/limits.md)); the UI shows the limit, a preview before upload, and typed errors `invalid_image` and `body_too_large`. A missing image shows initials on a tonal circle.

## States

| State | Behaviour |
|---|---|
| Loading | skeleton fields |
| Empty | Kindle: "No addresses yet" |
| Ready | forms; unsaved-change guard on leave |
| Error | inline field errors, `invalid_code`, `invalid_credentials`, `weak_password`, `limit_exceeded` |
| Forbidden | Kindle without the scope: section hidden; disabling a required TOTP: control disabled with reason |
| NotFound | not applicable |
| Offline | banner; theme change still works locally |

## Layout

compact: list of sections, each drills into a full screen; medium: rail plus section list left and form right; expanded and large: section list left, form right, centered measure.

## Copy keys

| Key | en | bn |
|---|---|---|
| `ux.settings.title` | Settings | সেটিংস |
| `ux.settings.theme` | Theme | থিম |
| `ux.settings.theme.system` | System | সিস্টেম |
| `ux.settings.theme.light` | Light | হালকা |
| `ux.settings.theme.dark` | Dark | গাঢ় |
| `ux.settings.language` | Language | ভাষা |
| `ux.settings.image.upload` | Upload photo | ছবি আপলোড করুন |
| `ux.settings.password.change` | Change password | পাসওয়ার্ড পরিবর্তন |
| `ux.settings.totp.enable` | Set up two-step verification | দ্বি-স্তর যাচাই চালু করুন |
| `ux.settings.kindle.title` | Kindle addresses | কিন্ডল ঠিকানা |
| `ux.settings.export` | Export my data | আমার তথ্য এক্সপোর্ট করুন |

Analytics: none. Accessibility: stepper dialog focus-trapped with step announcements; QR has the secret as text alternative; theme toggle is a labelled radio group; paste allowed in password and code fields.
