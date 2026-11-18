# 14f — notes: backend/catalog_management test_03 (201), test_04 (257)

Status: DRAFT (research evidence; read-only record)

- [CT22] staff (superadmin) POST /api/ingestion/duplicate-reviews/<id>/resolve/ {decision:"confirm_existing", notes} -> 200; submission.linked_book = existing_book, submission.status "ready", review.status "confirmed". Fixture: submission(input_type title, resolution_confidence 0.82, status duplicate, review_state needs_review) + DuplicateReview(submission, existing_book) — test_catalog_management_03.py:33
- [CT23] METADATA_EDIT book-scoped grant lets a non-staff user PATCH /api/catalog/books/<slug>/metadata/ {summary, notes} -> 200 — :67
- [CT24] metadata update dedups roles per person: payload [{ইশরাক, author},{ইশরাক, translator},{কেইগো, author},{কেইগো, editor}] -> stored (ইশরাক, translator) and (কেইগো, editor) ONLY; author role dropped when same name has translator or editor role — :85
- [CT25] METADATA_EDIT book grant allows DELETE /api/catalog/books/<slug>/ -> 204, soft delete: deleted_at set, state "soft_deleted" — :115
- [CT26] user without METADATA_EDIT DELETE book -> 403, deleted_at None — :130
- [CT27] PROCESSING_MANAGE global grant (non-staff) can resolve duplicate reviews (confirm_existing links book) — :143
- [CT28] metadata-reviews: POST /api/catalog/books/<slug>/metadata-reviews/ {state:"approved", notes} (editor with METADATA_EDIT) -> 201, book.review_state="approved", 1 MetadataReview; GET list -> [{state:"approved"}]; PATCH /api/catalog/metadata-reviews/<id>/ {state:"rejected",notes} -> 200, book.review_state "rejected" — :174
- [CT29] `?ownership=mine&sort=-requested_at`: only books where user has a submission linked; ordered by user's newest submission created_at desc (shared_book newest 2h ago before owner_book 2 days ago); other users' books excluded; rows have `latest_submission_at` (latest submission of THAT user) — test_catalog_management_04.py:35
- [CT30] book list paginated when `page` & `limit` given: `?record_type=all&sort=created_at&limit=2&page=2` -> `{entries:[...], pagination:{page, limit, total_count, page_count, has_previous, has_next}}`, `sort=created_at` ascending (third created book on page 2) — :96
- [CT31] book search normalises Bangla punctuation: q "অ আ ক খুনের কাঁটা" matches title "অ-আ-ক-খুনের কাঁটা"; `series=` filter "পি কে বাসু কাঁটা সিরিজ" matches "পি. কে. বাসু - কাঁটা সিরিজ"; `category=` "গোয়েন্দা ডিটেকটিভ" matches "গোয়েন্দা (ডিটেকটিভ)" — :119
- [CT32] performance rule: book list query must NOT select heavy columns summary, raw_scraped_metadata, raw_scrape_payload, main_content_html, book_info_html, dedication_html, toc, content_items (deferred) — :149
- [CT33] metadata editor POST /api/catalog/books/<slug>/assets/epub/ multipart `file` -> 200; replaces EPUB: asset.status ready, file_size = new length, legacy_path cleared "", new bytes stored in file field, OLD file deleted from disk, response `assets[]` includes epub — :188
- [CT34] metadata editor POST /api/catalog/books/<slug>/regenerate/ {} -> 202 `{created:true, job:{job_type:"reprocess"...}, book:{state:"processing", latest_processing_job:{status:"queued"}}}`; calls `queue_reprocess_book(book, actor=user)` (mocked in test via monkeypatch "apps.catalog.views.queue_reprocess_book") — :215
