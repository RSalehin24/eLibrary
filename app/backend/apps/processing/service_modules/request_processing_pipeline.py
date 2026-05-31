

def _scrape_heartbeat(request_id, stop_event):
    """Keep a PROCESSING request from looking stale during long scraping operations.

    Runs in a daemon thread and touches updated_at on the BookCreationRequest
    row every PROCESSING_SCRAPE_HEARTBEAT_INTERVAL seconds so the maintenance
    task does not mistake an actively-running scrape for a hung/stale request.
    """
    from django.db import close_old_connections  # local import — thread-safe
    while not stop_event.wait(PROCESSING_SCRAPE_HEARTBEAT_INTERVAL):
        try:
            close_old_connections()
            BookCreationRequest.objects.filter(
                pk=request_id,
                state=BookCreationRequestState.PROCESSING,
            ).update(updated_at=timezone.now())
        except Exception:
            logger.debug(
                "Scrape heartbeat update failed for request %s.", request_id, exc_info=True
            )
        finally:
            try:
                close_old_connections()
            except Exception:
                pass


def _processing_request_duplicate_check(processing_request, scraped_data):
    if processing_request.is_confirmed_not_duplicate:
        return None

    exact_title_duplicate = find_exact_existing_book(scraped_data)
    if exact_title_duplicate:
        return exact_title_duplicate

    if should_skip_processing_metadata_duplicate_check():
        return None

    metadata_duplicate = detect_metadata_duplicate(scraped_data)
    if metadata_duplicate:
        return metadata_duplicate

    return None


def _claim_unlinked_source_book(processing_request, candidate_book):
    if candidate_book is None:
        return False
    if duplicate_candidate_is_current_book(processing_request, candidate_book):
        return True
    if BookRecord.objects.filter(linked_book=candidate_book).exclude(
        pk=processing_request.book_record_id,
    ).exists():
        return False
    if BookCreationRequest.objects.filter(linked_book=candidate_book).exclude(
        pk=processing_request.pk,
    ).exists():
        return False

    processing_request.linked_book = candidate_book
    processing_request.save(update_fields=["linked_book", "updated_at"])
    return True


def _saved_scraped_data_for_resume(processing_request):
    saved_data = _request_saved_data(processing_request)
    checkpoint = _request_progress(processing_request).get("checkpoint") or ""
    scraped_data = saved_data.get("scrapedData")
    if not processing_request.is_resumed:
        return None
    if checkpoint != PROCESSING_SCRAPED_CONTENT_CHECKPOINT:
        return None
    if isinstance(scraped_data, dict):
        return scraped_data

    logger.warning(
        "Saved processing progress for request %s is corrupted. Falling back to a full restart.",
        processing_request.id,
    )
    return None


def _saved_curated_result_for_resume(processing_request):
    saved_data = _request_saved_data(processing_request)
    checkpoint = _request_progress(processing_request).get("checkpoint") or ""
    curated_result = saved_data.get("curatedResult")
    if not processing_request.is_resumed:
        return None
    if checkpoint != PROCESSING_SCRAPED_CONTENT_CHECKPOINT:
        return None
    return curated_result if isinstance(curated_result, dict) else None


SIGN_IN_REQUIRED_TOC_ERROR = (
    "Sign-in required: the source table of contents spans multiple pages on "
    "ebanglalibrary.com but only {fetched} of {source} TOC pages could be "
    "retrieved. Update the ebanglalibrary.com auth cookie and regenerate this book."
)

CONTENT_FETCH_INCOMPLETE_ERROR = (
    "Incomplete scrape: only {fetched} of {expected} topic pages returned content. "
    "The source may be rate-limiting requests — please try regenerating."
)


def _source_structure_from_curated(curated_result):
    if not isinstance(curated_result, dict):
        return {}
    snapshot = curated_result.get("source_snapshot")
    if not isinstance(snapshot, dict):
        return {}
    manifest = snapshot.get("manifest")
    if not isinstance(manifest, dict):
        return {}
    structure = manifest.get("source_structure")
    return structure if isinstance(structure, dict) else {}


def _apply_multi_page_toc_signal(processing_request, curated_result):
    """Persist multi-page TOC signals and fail the request when pages are missing.

    The LearnDash AJAX pager only returns later TOC pages for an authenticated
    session. When the ebanglalibrary.com sign-in cookie is missing or expired,
    pages beyond the first yield no new lessons, so the book would be created
    with only a fraction of its content. We surface that as an explicit failure
    instead of silently producing an incomplete book.
    """
    structure = _source_structure_from_curated(curated_result)

    def _coerce_int(value, default):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    has_paginated = bool(structure.get("has_paginated_toc"))
    source_pages = _coerce_int(structure.get("source_total_pages"), 1)
    attempted_pages = _coerce_int(structure.get("fetched_total_pages"), 1)
    fetched_pages = _coerce_int(structure.get("toc_pages_with_content"), 0)
    toc_incomplete = bool(structure.get("toc_incomplete"))

    total_pages = max(source_pages, attempted_pages, 1)
    processing_request.has_multi_page_toc = has_paginated
    processing_request.source_toc_page_count = total_pages
    processing_request.fetched_toc_page_count = max(fetched_pages, 0)
    processing_request.save(
        update_fields=[
            "has_multi_page_toc",
            "source_toc_page_count",
            "fetched_toc_page_count",
            "updated_at",
        ]
    )

    if toc_incomplete:
        # Message intentionally mentions "ebanglalibrary.com" so the retry loop in
        # _run_processing_request stops retrying (re-scraping cannot recover the
        # missing pages until the auth cookie is refreshed).
        raise ValueError(
            SIGN_IN_REQUIRED_TOC_ERROR.format(
                fetched=max(fetched_pages, 0),
                source=total_pages,
            )
        )

    content_incomplete = bool(structure.get("content_incomplete"))
    topics_expected = _coerce_int(structure.get("topics_expected"), 0)
    topics_fetched = _coerce_int(structure.get("topics_fetched"), 0)
    if content_incomplete:
        # Does NOT contain "ebanglalibrary.com" so the retry loop will attempt up
        # to MAX_PROCESSING_REQUEST_ATTEMPTS re-scrapes (transient rate-limiting
        # may clear between attempts). The pipeline fails *before*
        # _persist_processing_book so book.content_items is never overwritten with
        # the partial scrape result.
        raise ValueError(
            CONTENT_FETCH_INCOMPLETE_ERROR.format(
                fetched=topics_fetched,
                expected=topics_expected,
            )
        )


def _process_request_once(processing_request):
    processing_request = _reload_processing_request(processing_request.id)
    if processing_request.state in TERMINAL_STATES or processing_request.state == BookCreationRequestState.PAUSED:
        sync_record_state(processing_request.book_record)
        return processing_request

    normalized_url = normalize_source_url(processing_request.book_record.url)
    source_metadata = capture_source_page_metadata(normalized_url)
    if source_metadata:
        _update_record_from_source_metadata(processing_request.book_record, source_metadata)

    processing_request = _reload_processing_request(processing_request.id)
    if processing_request.state == BookCreationRequestState.DELETED:
        sync_record_state(processing_request.book_record)
        return processing_request
    if processing_request.state == BookCreationRequestState.PAUSED:
        return _save_paused_processing_progress(
            processing_request.id,
            PROCESSING_SOURCE_METADATA_CHECKPOINT,
            {"sourceMetadata": source_metadata or {}},
        )

    if not processing_request.is_confirmed_not_duplicate:
        source_duplicate = find_existing_book_by_source_url(normalized_url)
        if source_duplicate and not duplicate_candidate_is_current_book(
            processing_request,
            source_duplicate,
        ):
            if _claim_unlinked_source_book(processing_request, source_duplicate):
                processing_request = _reload_processing_request(processing_request.id)
            else:
                return _mark_request_duplicate(processing_request, source_duplicate)

        if source_duplicate and not duplicate_candidate_is_current_book(
            processing_request,
            source_duplicate,
        ):
            return _mark_request_duplicate(processing_request, source_duplicate)

    curated_result = _saved_curated_result_for_resume(processing_request)
    scraped_data = _saved_scraped_data_for_resume(processing_request)
    legacy_scrape_overridden = False
    if curated_result is None:
        legacy_scrape_overridden = getattr(scrape_book, "__module__", "") != "apps.processing.source"
        if legacy_scrape_overridden:
            raw_scraped_data = scrape_book(normalized_url)
            curated_result = curate_scraped_book_data(normalized_url, raw_scraped_data)
        else:
            _stop_heartbeat = threading.Event()
            _heartbeat_thread = threading.Thread(
                target=_scrape_heartbeat,
                args=(processing_request.id, _stop_heartbeat),
                daemon=True,
                name=f"scrape-heartbeat-{processing_request.id}",
            )
            _heartbeat_thread.start()
            try:
                curated_result = curate_book(normalized_url)
            finally:
                _stop_heartbeat.set()
                _heartbeat_thread.join(timeout=5)
        scraped_data = curated_result.get("projection", {})
        if isinstance(scraped_data, dict) and not scraped_data.get("book_title"):
            scraped_data = {
                **scraped_data,
                "book_title": processing_request.book_record.name,
                "author": processing_request.book_record.writer,
                "series": "",
                "book_type": processing_request.book_record.category,
            }
            document = curated_document_with_projection(curated_result["document"], scraped_data)
            curated_result = {
                **curated_result,
                "document": document,
                "projection": document["projection"],
            }
        if not isinstance(scraped_data, dict):
            raise ValueError(
                f"Source curation returned no content for {normalized_url}. "
                "Verify the source URL is valid and publicly reachable."
            )
    elif scraped_data is None:
        scraped_data = curated_result.get("projection", {})

    processing_request = _reload_processing_request(processing_request.id)
    if processing_request.state == BookCreationRequestState.DELETED:
        sync_record_state(processing_request.book_record)
        return processing_request

    # Save multi-page TOC detection fields now — before the PAUSED branch — so
    # that books paused after a long scrape still appear on the Multi-page TOC
    # page. If the TOC is incomplete (sign-in required), the resulting ValueError
    # propagates to _fail_processing_request which safely no-ops for PAUSED state.
    _apply_multi_page_toc_signal(processing_request, curated_result)

    if processing_request.state == BookCreationRequestState.PAUSED:
        return _save_paused_processing_progress(
            processing_request.id,
            PROCESSING_SCRAPED_CONTENT_CHECKPOINT,
            {"scrapedData": scraped_data, "curatedResult": curated_result},
        )

    duplicate_book = _processing_request_duplicate_check(
        processing_request,
        scraped_data,
    )
    if duplicate_book and not duplicate_candidate_is_current_book(
        processing_request,
        duplicate_book,
    ):
        return _mark_request_duplicate(processing_request, duplicate_book)

    if (
        not legacy_scrape_overridden
        and curated_result.get("status") == CuratedDocumentStatus.INVALID
        and not scraped_data.get("book_title")
    ):
        raise ValueError("Curated document requires review before a book can be created.")

    book = _persist_processing_book(
        processing_request,
        normalized_url,
        scraped_data,
        curated_result=curated_result,
        force=bool(processing_request.force_generate),
    )
    if (
        not legacy_scrape_overridden
        and curated_result.get("status") != CuratedDocumentStatus.VALIDATED
        and not processing_request.force_generate
    ):
        return _mark_request_review_required(processing_request, book, curated_result)
    return _finalize_processing_request(processing_request, book, scraped_data)


def _fail_processing_request(processing_request, error):
    processing_request = _reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    if processing_request.state in {
        BookCreationRequestState.DELETED,
        BookCreationRequestState.PAUSED,
    }:
        sync_record_state(processing_request.book_record)
        return processing_request

    processing_request.state = BookCreationRequestState.FAILED
    processing_request.error_message = str(error)
    processing_request.save(update_fields=["state", "error_message", "updated_at"])
    sync_record_state(processing_request.book_record)
    publish_processing_ui_domains(
        processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.FAILED,
            record=processing_request.book_record,
        )
    )
    return processing_request


def _mark_request_review_required(processing_request, book, curated_result):
    processing_request = _reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    if processing_request.state in {
        BookCreationRequestState.DELETED,
        BookCreationRequestState.PAUSED,
    }:
        sync_record_state(processing_request.book_record)
        return processing_request

    processing_request.state = BookCreationRequestState.FAILED
    processing_request.linked_book = book
    processing_request.error_message = "Curated document requires review before asset generation."
    processing_request.progress = {
        "curatedValidation": curated_result.get("validation", {}),
        "curatedStatus": curated_result.get("status", ""),
    }
    processing_request.save(update_fields=["state", "linked_book", "error_message", "progress", "updated_at"])
    sync_record_state(processing_request.book_record)
    publish_processing_ui_domains(
        processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.FAILED,
            record=processing_request.book_record,
        )
    )
    return processing_request


CONTENT_INCOMPLETE_RETRY_DELAY = 60  # seconds


def _run_processing_request(processing_request):
    last_error = None
    for _attempt in range(MAX_PROCESSING_REQUEST_ATTEMPTS):
        try:
            return _process_request_once(processing_request)
        except Exception as exc:
            last_error = exc
            logger.exception(
                "Processing request %s failed.",
                processing_request.id,
            )
            if (
                isinstance(exc, ValueError)
                and "ebanglalibrary.com" in str(exc)
            ):
                break
            reloaded = _reload_processing_request(processing_request.id)
            if reloaded.state in {
                BookCreationRequestState.DELETED,
                BookCreationRequestState.PAUSED,
            }:
                return reloaded
            is_last_attempt = _attempt >= MAX_PROCESSING_REQUEST_ATTEMPTS - 1
            if (
                not is_last_attempt
                and isinstance(exc, ValueError)
                and str(exc).startswith("Incomplete scrape:")
            ):
                logger.info(
                    "Processing request %s: incomplete content scrape on attempt %d/%d. "
                    "Waiting %ds before retry.",
                    processing_request.id,
                    _attempt + 1,
                    MAX_PROCESSING_REQUEST_ATTEMPTS,
                    CONTENT_INCOMPLETE_RETRY_DELAY,
                )
                time.sleep(CONTENT_INCOMPLETE_RETRY_DELAY)
    return _fail_processing_request(processing_request, last_error or PROCESSING_STALE_MESSAGE)


def _transition_request_state(request_id, from_state, to_state):
    with transaction.atomic():
        processing_request = (
            BookCreationRequest.objects.select_for_update().get(pk=request_id)
        )
        if processing_request.state != from_state:
            return processing_request
        processing_request.state = to_state
        update_fields = ["state", "error_message", "updated_at"]
        if to_state == BookCreationRequestState.PROCESSING:
            processing_request.error_message = ""
            next_progress = _request_progress_without_dispatch_marker(
                processing_request.progress
            )
            if next_progress != processing_request.progress:
                processing_request.progress = next_progress
                update_fields.append("progress")
        processing_request.save(update_fields=update_fields)
        sync_record_state(processing_request.book_record)
        publish_processing_ui_domains(
            processing_domains_for_request_change(
                from_state,
                to_state,
                record=processing_request.book_record,
            )
        )
        return processing_request


def kickoff_request_processing(request_id, actor=None):
    processing_request = _reload_processing_request(request_id)
    if processing_request.state == BookCreationRequestState.INITIAL:
        processing_request = _transition_request_state(
            request_id,
            BookCreationRequestState.INITIAL,
            BookCreationRequestState.QUEUED,
        )
    if processing_request.state == BookCreationRequestState.QUEUED:
        processing_request = _transition_request_state(
            request_id,
            BookCreationRequestState.QUEUED,
            BookCreationRequestState.PROCESSING,
        )
    if processing_request.state == BookCreationRequestState.PROCESSING:
        return _run_processing_request(processing_request)
    sync_record_state(processing_request.book_record)
    return processing_request
