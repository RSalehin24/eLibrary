# Account navigation and login challenges

Profiles contain personal settings and security. Authorized accounts have a
prominent **পরিচালনা** header link and a **পরিচালনায় যান** profile button.
Management has direct shortcuts to source import, manual entry, and processing
jobs, each limited by the existing backend workspace permissions. Navigation
marks the current section; readers receive no administrative shortcuts or access.

The login form initially asks only for email and password. After authenticating
those credentials, the existing API returns `otp_required` only for an account
with two-factor authentication enabled. The form then reveals and focuses the
required security-code field. Six-digit app codes and eight-digit backup codes
remain supported. Invalid credentials do not reveal the field; changing either
credential discards the old challenge. Invalid codes and temporary failures keep
the selected account's code available for correction without signing it in.

The shared native SVG book-and-bookmark mark appears in the header, footer and
login welcome panel. Version-two application icons reuse that artwork; immutable
version-one icons remain available for existing installations. Public installation
previews have new content-addressed filenames. Responsive checks include enlarged
text at 320 pixels and minimum 44-pixel account controls.
