# 14c — notes: backend/access test_access_01 (+cases: download_reader_and_kindle 407, kindle_smtp_failures 243, kindle_validation_and_html_downloads 99, facade 16)

Status: DRAFT (research evidence; read-only record)
Fixtures pattern: Book(title, state="ready", review_state="approved") + GeneratedAsset(asset_type EPUB/HTML/COVER, status READY, legacy_path=<tmp file>, file_size) + PermissionGrant(user, book, scope).
Routes: GET /api/access/books/<slug>/download/{epub|html|cover}/, POST /api/access/books/<slug>/reader-launch/, POST /api/access/books/<slug>/send-to-kindle/

- [AC1] given user without grant, GET download/epub -> 403; with book-scoped DOWNLOAD_FILE grant -> 200 and Content-Disposition filename "Access Book.epub" (either `filename="X"` or RFC5987 `filename*=utf-8''<quoted>`) — download_reader_and_kindle.py:37
- [AC2] with PREVIEW_HTML grant, POST reader-launch -> 200 `{manifest_url}`; GET manifest_url -> 200 with `book.slug`, `reading_session_url`, `bookmarks_url` — :37-83
- [AC3] book OWNER (user has a BookSubmission with linked_book=book, status READY, resolution RESOLVED, input_type url) needs no explicit grants: list `/api/catalog/books/?ownership=mine` first row has `cover_download_url` ending `/api/access/books/<slug>/download/cover/`; book detail `assets[]` entries have `asset_type` + `download_url` for cover/html/epub; all three downloads 200 and reader-launch 200 — :85
- [AC4] download filenames use CURRENT book title, not stored file name: title "বর্তমান বই নাম" -> epub "বর্তমান বই নাম.epub", cover "বর্তমান বই নাম.jpg"; reader manifest `epub_download_url` also serves with the same filename — :155
- [AC5] send-to-kindle: user.kindle_emails=[a@kindle.com,b@kindle.com], SEND_KINDLE grant -> 200 payload `{deliveredEmails:[both], failedEmails:[], senderEmail:<ACCOUNT_INVITE_FROM_EMAIL>}`; one mail per address, empty body, attachment[0] filename "<Book Title>.epub" — :205
- [AC6] READ_ONCE grant: first reader-launch 200, second 403 — :238
- [AC7] READ_ONCE + PREVIEW_HTML: first GET download/html 200, second 403 (HTML preview counts as the one read) — :266
- [AC8] READ_ONCE + PREVIEW_HTML: after one HTML download, reader-launch 403 (HTML and reader share the single "once") — :295
- [AC9] READ_ONCE alone (no PREVIEW_HTML): download/html 403 (not consumed), reader-launch #1 200, #2 403 — :334
- [AC10] read:once and read:durable mutually exclusive: ManagedUserCreateSerializer with global_scopes ["read:once","read:durable"] invalid (error key `global_scopes`); PermissionGrantSerializer for a (user,book) already holding READ_ONCE adding read:durable invalid, message mentions "Read Once and Durable Read" — :376
- [AC11] Kindle via Brevo: when EMAIL_BACKEND is `anymail.backends.brevo.EmailBackend` (an API backend that cannot be used for attachments to Kindle), view builds an SMTP connection `django.core.mail.backends.smtp.EmailBackend` explicitly (get_connection(backend=smtp, host=EMAIL_HOST, port, username=EMAIL_HOST_USER, password=EMAIL_HOST_PASSWORD, use_tls)) and closes it; message body is "" — kindle_smtp_failures.py:12, :77
- [AC12] missing SMTP host/password -> 502 with detail containing "Kindle delivery requires SMTP", `failedEmails:[addr]`, `senderEmail` — :144
- [AC13] SMTPAuthenticationError(535) -> 502 detail contains "could not authenticate with Brevo SMTP" and "API key will not work for SMTP"; failedEmails=[addr]; connection closed — :184
- [AC14] kindle_emails not ending @kindle.com (legacy data "reader-two@example.com") are ignored at send time: only valid one delivered, failedEmails [] — kindle_validation_and_html_downloads.py:4
- [AC15] no Kindle emails configured -> 400 detail "Add at least one Kindle email in your profile before sending." — :36
- [AC16] HTML download inlines stale relative cover refs: HTML `<img src='book_image.hpg' class='cover-image'>` + ready COVER asset -> response contains `data:image/jpeg;base64,` and not the original src — :63

Mock heavy: monkeypatch of apps.access.views.assets.get_connection and EmailMessage.send (module path `apps.access.views.assets`).
