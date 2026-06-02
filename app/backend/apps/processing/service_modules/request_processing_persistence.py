

def _request_saved_data(processing_request):
    progress = _request_progress(processing_request)
    saved_data = progress.get("savedData")
    return saved_data if isinstance(saved_data, dict) else {}


def _request_dispatch_pending(processing_request):
    if processing_request.state not in {
        BookCreationRequestState.INITIAL,
        BookCreationRequestState.QUEUED,
    }:
        return False

    progress = _request_progress(processing_request)
    requested_at_raw = progress.get(PROCESSING_DISPATCH_REQUESTED_AT_KEY)
    if not requested_at_raw:
        return False

    requested_at = parse_datetime(str(requested_at_raw))
    if requested_at is None:
        return False
    if timezone.is_naive(requested_at):
        requested_at = timezone.make_aware(requested_at, timezone.get_current_timezone())

    return (timezone.now() - requested_at) < PROCESSING_DISPATCH_STALE_AFTER


def _request_progress_without_dispatch_marker(progress):
    if not isinstance(progress, dict):
        return progress

    next_progress = dict(progress)
    next_progress.pop(PROCESSING_DISPATCH_REQUESTED_AT_KEY, None)
    next_progress.pop(PROCESSING_DISPATCH_TASK_ID_KEY, None)
    return next_progress or None


def _reload_processing_request(request_id):
    return (
        BookCreationRequest.objects.select_related("book_record", "linked_book")
        .get(pk=request_id)
    )


def _update_record_from_source_metadata(record, metadata):
    if not isinstance(metadata, dict):
        return record

    before_snapshot = processing_record_snapshot(record)
    source_entry = upsert_source_catalog_entry(metadata)
    raw_data = metadata.get("raw_data") if isinstance(metadata.get("raw_data"), dict) else {}
    desired_values = {
        "name": metadata.get("title") or record.name,
        "writer": metadata.get("author_line") or record.writer,
        "category": raw_data.get("category") or record.category,
        "translator": raw_data.get("translator") or record.translator,
        "composer": raw_data.get("composer") or record.composer,
        "publisher": raw_data.get("publisher") or record.publisher,
        "source_catalog_entry": source_entry,
    }
    update_fields = [
        field_name
        for field_name, value in desired_values.items()
        if getattr(record, field_name) != value
    ]
    if update_fields:
        for field_name in update_fields:
            setattr(record, field_name, desired_values[field_name])
        record.save(update_fields=[*update_fields, "updated_at"])
        _latest_request = latest_request_for_record(record)
        publish_processing_ui_domains(
            processing_domains_for_record_change(
                before_snapshot,
                processing_record_snapshot(record),
                current_request_state=(
                    _latest_request.state
                    if _latest_request
                    else None
                ),
            )
        )
    return record


def _build_processing_progress(checkpoint, saved_data):
    return {
        "savedAt": timezone.now().isoformat(),
        "checkpoint": checkpoint,
        "savedData": saved_data if isinstance(saved_data, dict) else {},
    }


def _save_paused_processing_progress(request_id, checkpoint, saved_data):
    processing_request = _reload_processing_request(request_id)
    if processing_request.state != BookCreationRequestState.PAUSED:
        return processing_request

    processing_request.progress = _build_processing_progress(checkpoint, saved_data)
    processing_request.error_message = ""
    processing_request.save(update_fields=["progress", "error_message", "updated_at"])
    sync_record_state(processing_request.book_record)
    publish_processing_ui_domains(
        processing_domains_for_request_change(
            BookCreationRequestState.PAUSED,
            BookCreationRequestState.PAUSED,
            record=processing_request.book_record,
        )
    )
    return processing_request


def _duplicate_targets(existing_book, processing_request):
    target_request = (
        BookCreationRequest.objects.filter(linked_book=existing_book)
        .exclude(pk=processing_request.pk)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    if target_request:
        return target_request, target_request.book_record

    target_record = (
        BookRecord.objects.filter(linked_book=existing_book)
        .exclude(pk=processing_request.book_record_id)
        .order_by("-updated_at", "-created_at")
        .first()
    )
    return None, target_record


def _mark_request_duplicate(processing_request, existing_book):
    processing_request = _reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    record_before = processing_record_snapshot(processing_request.book_record)
    target_request, target_record = _duplicate_targets(existing_book, processing_request)
    processing_request.state = BookCreationRequestState.DUPLICATE
    processing_request.linked_book = existing_book
    processing_request.duplicate_of_request = target_request
    processing_request.duplicate_of_record = target_record
    processing_request.error_message = ""
    processing_request.save(
        update_fields=[
            "state",
            "linked_book",
            "duplicate_of_request",
            "duplicate_of_record",
            "error_message",
            "updated_at",
        ]
    )

    record = processing_request.book_record
    record.linked_book = existing_book
    record.is_duplicate = True
    record.duplicate_of_record = target_record
    record.save(update_fields=["linked_book", "is_duplicate", "duplicate_of_record", "updated_at"])
    sync_record_state(record)
    publish_processing_ui_domains(
        processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.DUPLICATE,
            record=record,
        )
        | processing_domains_for_record_change(
            record_before,
            processing_record_snapshot(record),
            current_request_state=BookCreationRequestState.DUPLICATE,
        )
    )
    return processing_request


def duplicate_candidate_is_current_book(processing_request, candidate_book):
    if candidate_book is None:
        return False

    current_book = processing_linked_book(
        processing_request.book_record,
        processing_request,
    )
    return bool(current_book and current_book.id == candidate_book.id)


def _persist_processing_book(processing_request, normalized_url, scraped_data, curated_result=None, *, force=False):
    submission_stub = SimpleNamespace(resolved_url=normalized_url)
    target_book = (
        processing_request.linked_book
        if processing_request.linked_book_id and processing_request.linked_book and processing_request.linked_book.deleted_at is None
        else None
    )
    document_for_export = None
    if curated_result is not None:
        book, _curated_document = persist_curated_book(
            submission_stub,
            None,
            curated_result,
            target_book=target_book,
        )
        not_validated = curated_result.get("status") != CuratedDocumentStatus.VALIDATED
        if not_validated and not force:
            return book
        document_for_export = curated_result["document"]
        if not_validated and force:
            # Force generation bypasses the review gate; apply the same
            # automatic mitigations the manual Force Generate action used to
            # apply inline so a review-required document can still export.
            document_for_export, chrome_stripped = _strip_source_chrome_from_document(
                document_for_export
            )
            document_for_export, dupes_fixed = _fix_duplicate_paths_in_document(
                document_for_export
            )
            if chrome_stripped:
                logger.info(
                    "Force-generate request %s: stripped %d source-chrome block(s).",
                    processing_request.id,
                    chrome_stripped,
                )
            if dupes_fixed:
                logger.info(
                    "Force-generate request %s: resolved %d duplicate content path(s).",
                    processing_request.id,
                    dupes_fixed,
                )
    else:
        book = persist_scraped_book(submission_stub, None, scraped_data, target_book=target_book)
    export_payload = export_payload_from_book(book, scraped_data)
    generate_exports(
        curated_document_with_projection(document_for_export, export_payload)
        if document_for_export is not None
        else export_payload
    )
    sync_assets(book, None, export_payload)
    return book


def _finalize_processing_request(processing_request, book, scraped_data):
    processing_request = _reload_processing_request(processing_request.id)
    previous_state = processing_request.state
    record_before = processing_record_snapshot(processing_request.book_record)
    if processing_request.state == BookCreationRequestState.DELETED:
        if book.deleted_at is None:
            book.soft_delete()
        sync_record_state(processing_request.book_record)
        return processing_request
    if processing_request.state == BookCreationRequestState.PAUSED:
        _save_paused_processing_progress(
            processing_request.id,
            PROCESSING_SCRAPED_CONTENT_CHECKPOINT,
            {
                "scrapedData": scraped_data if isinstance(scraped_data, dict) else {},
                "linkedBookId": str(book.id),
            },
        )
        return _reload_processing_request(processing_request.id)

    processing_request.state = BookCreationRequestState.CREATED
    processing_request.linked_book = book
    processing_request.error_message = ""
    processing_request.progress = None
    processing_request.force_generate = False
    processing_request.save(
        update_fields=["state", "linked_book", "error_message", "progress", "force_generate", "updated_at"]
    )
    record = processing_request.book_record
    record_update_fields = []
    if record.linked_book_id != book.id:
        record.linked_book = book
        record_update_fields.append("linked_book")
    if record.is_duplicate:
        record.is_duplicate = False
        record_update_fields.append("is_duplicate")
    if record.duplicate_of_record_id:
        record.duplicate_of_record = None
        record_update_fields.append("duplicate_of_record")
    if record_update_fields:
        record.save(update_fields=[*record_update_fields, "updated_at"])
    sync_record_state(record)
    publish_processing_ui_domains(
        processing_domains_for_request_change(
            previous_state,
            BookCreationRequestState.CREATED,
            record=record,
        )
        | processing_domains_for_record_change(
            record_before,
            processing_record_snapshot(record),
            current_request_state=BookCreationRequestState.CREATED,
        )
    )
    # Clean up the disk scrape-cache so it doesn't consume storage after a
    # successful build.
    try:
        from apps.processing.service_modules.scrape_cache import (  # noqa: PLC0415
            DiskPageCache,
            scrape_cache_path_for_request,
        )
        DiskPageCache(scrape_cache_path_for_request(processing_request.id)).delete()
    except Exception:
        pass  # non-fatal
    return processing_request
