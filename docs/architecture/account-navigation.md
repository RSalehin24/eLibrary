# Account navigation and login challenges

Profiles contain personal settings and security. Authorized accounts have a
prominent **অ্যাডমিন** header link and an **অ্যাডমিন প্যানেল** profile button.
Management has direct shortcuts to source import, manual entry, and processing
jobs, each limited by the existing backend workspace permissions. Navigation
marks the current section; readers receive no administrative shortcuts or access.

The entire new website supports English and Bengali: public browsing, login and
password recovery, personal books/notes, profile/security, Kindle controls,
reader controls, and management. The header switch preserves typed values,
selected books/files, and reader settings. A whitelisted `library-language`
cookie supplies private server rendering and subsequent navigation; the older
admin cookie remains a compatible fallback. Bengali is the default. Authored
labels, accessible names, page titles, dates, numbers and supported validation
messages follow the preference. Book titles, authors, source text and personal
notes remain their original data. Unknown diagnostic strings remain inspectable.
The offline document contains both languages without requiring an account or
caching private content.

Administration has its own header, always-visible section navigation and compact
creation workspace. Fetch All, Process All, Schedule Automation and Manual Upload
are direct controls. Phone navigation remains visible without a disclosure.
Links have no text decoration; hover and keyboard focus provide visible feedback.

Public and administrative pages now share the same green/neutral palette,
controls and self-hosted Noto Sans Bengali font assets, reused from the existing
EPUB assets. The public home focuses on searching and published books rather than
decorative sample book covers. Repeated admin workflow navigation and large
control summary cards were removed so search and book rows are visible earlier.
Selection actions appear when records are selected. Profiles have direct section
anchors and a two-column identity/photo layout on wider screens; jumping to
security or password settings preserves unsaved forms.

Dates use an explicit numbering system (`beng` in Bengali, `latn` in English), a
24-hour clock and localized zone label. UTC remains the stored/displayed zone;
Bengali no longer mixes English AM/PM/UTC into the timestamp. Explicit numbering
also avoids Safari's differing Bengali locale default.

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
