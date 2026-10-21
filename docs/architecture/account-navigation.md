# Account navigation and login challenges

Profiles contain personal settings and security. Administrators default to
`/manage/` after sign-in, which redirects to Book Creation or their first allowed
management section. The overview remains at `/manage/overview/`. Ordinary readers
default to `/my-books/`. Explicit safe
return links and required authenticator setup retain precedence. Administration
has a separate header and permission-filtered section navigation. Management
keeps direct shortcuts to source import, manual entry and processing jobs.

**Reader View** opens the administrator's personal library with the same account,
general navigation and personal settings. **Return to Admin** restores management.
The `library-workspace-view` preference contains the account ID and selected view,
so another account cannot inherit it. It never grants or revokes permissions.
Changing view performs a document navigation after setting the preference, avoiding
stale prefetched layouts. A new sign-in clears the previous preference. Ordinary
reader accounts cannot obtain management navigation or API access through a cookie.
Administrative shortcuts on reader pages appear only in the admin view.

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
caching private content. Static pages restore the cookie after hydration through
the same language subscription; language changes and window focus update mounted
views. Streamed route metadata is relocalized when it arrives, with unchanged
titles left untouched to avoid observer loops.

Administration has its own header, six permission-filtered sections and compact
creation workspace. Book Creation, Books, Authors & Categories, Processing,
Schedules and Users use a desktop sidebar and a labelled phone drawer. The drawer
supports Escape, focus return and closing after navigation. Fetch All, Process All,
Upload EPUB, Add Paper Book and Schedule Automation are direct creation controls.
Selection controls appear after selection. Source rows use the actual active job
state, distinguishing queued, running, retry, paused and attention states.

Reader navigation has My Books, Browse Books, Notes and Kindle. On phones those
four labelled destinations form the bottom navigation. Profile, paper books,
local EPUB, help and sign-out use the account menu. Language stays visible on
desktop and is available inside the mobile account menu without losing forms.
Account/menu icons retain accessible names and touch targets. Related public
metadata pages retain Browse as the current section.
Links have no text decoration; hover and keyboard focus provide visible feedback.

Public and administrative pages now share the same green/neutral palette,
controls and self-hosted Noto Sans Bengali font assets, reused from the existing
EPUB assets. The public home focuses on searching and published books rather than
decorative sample book covers. Repeated admin workflow navigation and large
control summary cards were removed so search and book rows are visible earlier.
Selection actions appear when records are selected. Profiles have direct section
anchors and a two-column identity/photo layout on wider screens; jumping to
security or password settings preserves unsaved forms.

Dates display in **Asia/Dhaka with a 12-hour clock**, using an explicit numbering
system (`beng` in Bengali, `latn` in English) and localized day-period/zone labels.
Storage remains UTC. Explicit numbering also avoids Safari's differing Bengali
locale default. Scheduling and expiry inputs retain explicit AM/PM controls.

The login form initially asks only for email and password. After authenticating
those credentials, the existing API returns `otp_required` only for an account
with two-factor authentication enabled. The form then reveals and focuses the
required security-code field. Six-digit app codes and eight-digit backup codes
remain supported. Invalid credentials do not reveal the field; changing either
credential discards the old challenge. Invalid codes and temporary failures keep
the selected account's code available for correction without signing it in.

The native SVG logo combines the book-and-bookmark mark and **বাংলা পাঠাগার**
wordmark. The name stays Bengali in both interface languages and is not repeated
beside the logo. It appears in the header, footer and login welcome panel.
Version-two application icons reuse the mark; immutable
version-one icons remain available for existing installations. Public installation
previews have new content-addressed filenames. Responsive checks include enlarged
text at 320 pixels and minimum 44-pixel account controls.

List pagination exposes actual totals, first/last pages, the current page and a
bounded neighboring window with ellipses. Phones use a shorter window; enlarged
text reflows the previous/next controls. Filters and sorting survive a page jump.
Catalog and personal feeds expose additive exact count metadata while retaining
their cursor fields. Website links remove retired book-type and added/request-date
filters, resetting pagination only when those conditions were actually supplied.
Generated pagination and My Books tab links never reintroduce retired conditions. Counts respect the same visibility and filtering as results.
See [the sitewide review](../operations/sitewide-ui-review.md) for the page inventory,
screenshots, defects corrected and verification evidence.
