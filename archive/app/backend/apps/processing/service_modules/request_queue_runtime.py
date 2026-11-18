

def next_request_id(preferred_id):
    if not BookCreationRequest.objects.filter(pk=preferred_id).exists():
        return preferred_id
    index = 2
    while BookCreationRequest.objects.filter(pk=f"{preferred_id}-{index}").exists():
        index += 1
    return f"{preferred_id}-{index}"


def request_blocks_record_selection(request):
    return request and request.state not in {
        BookCreationRequestState.FAILED,
        BookCreationRequestState.DELETED,
    }


def record_is_selectable(record):
    if not can_process_record_url(record.url):
        return False
    requests = record_request_list(record)
    duplicate_request = next(
        (
            request
            for request in requests
            if request.state == BookCreationRequestState.DUPLICATE and request.duplicate_confirmed
        ),
        None,
    )
    if duplicate_request:
        original = duplicate_request.duplicate_of_request
        return original is None or original.state in {
            BookCreationRequestState.FAILED,
            BookCreationRequestState.DELETED,
        }
    if record.linked_book_id and not requests:
        return False
    return not any(request_blocks_record_selection(request) for request in requests)


def enqueue_request_processing(processing_request):
    from apps.ingestion.engine.dispatch import dispatch_job

    processing_request = _reload_processing_request(processing_request.id)
    if processing_request.state == BookCreationRequestState.INITIAL:
        processing_request = _transition_request_state(
            processing_request.id,
            BookCreationRequestState.INITIAL,
            BookCreationRequestState.QUEUED,
        )
    if processing_request.state != BookCreationRequestState.QUEUED:
        return False
    if _request_dispatch_pending(processing_request):
        return False

    try:
        dispatch_job(
            job_id=str(processing_request.id),
            job_type="pipeline",
            handler="pipeline",
        )
    except Exception:
        logger.warning(
            "Engine pipeline dispatch failed for %s.",
            processing_request.id,
            exc_info=True,
        )
        return False

    processing_request = _reload_processing_request(processing_request.id)
    if processing_request.state == BookCreationRequestState.QUEUED:
        next_progress = {
            **_request_progress(processing_request),
            PROCESSING_DISPATCH_REQUESTED_AT_KEY: timezone.now().isoformat(),
        }
        processing_request.progress = next_progress
        processing_request.save(update_fields=["progress", "updated_at"])
    return True


def queue_processing_request(processing_request):
    if not can_process_record_url(processing_request.book_record.url):
        return _fail_processing_request(
            processing_request,
            ValueError("Only source site book URLs are allowed"),
        )
    if should_enqueue_processing_work():
        if enqueue_request_processing(processing_request):
            return _reload_processing_request(processing_request.id)
        return kickoff_request_processing(processing_request.id)
    if should_run_processing_jobs_inline():
        return kickoff_request_processing(processing_request.id)
    return _reload_processing_request(processing_request.id)


def collect_processing_task_ids():
    task_ids = {
        str(task_id).strip()
        for task_id in ProcessingSyncState.objects.exclude(task_id="").values_list(
            "task_id",
            flat=True,
        )
        if str(task_id).strip()
    }
    for progress in BookCreationRequest.objects.exclude(progress__isnull=True).values_list(
        "progress",
        flat=True,
    ):
        if not isinstance(progress, dict):
            continue
        task_id = str(progress.get(PROCESSING_DISPATCH_TASK_ID_KEY) or "").strip()
        if task_id:
            task_ids.add(task_id)
    return task_ids


def revoke_processing_task_ids(task_ids, *, terminate=False):
    revoked = set()
    for task_id in task_ids or []:
        normalized_task_id = str(task_id or "").strip()
        if not normalized_task_id:
            continue
        try:
            celery_app.control.revoke(normalized_task_id, terminate=terminate)
        except Exception:
            logger.warning(
                "Failed to revoke processing task %s.",
                normalized_task_id,
                exc_info=True,
            )
            continue
        revoked.add(normalized_task_id)
    return revoked


def purge_processing_task_queue():
    try:
        with celery_app.connection_or_acquire() as connection:
            queue = Queue(
                PROCESSING_TASK_QUEUE,
                routing_key=PROCESSING_TASK_QUEUE,
            ).bind(connection.default_channel)
            return int(queue.purge() or 0)
    except Exception:
        logger.warning(
            "Failed to purge processing task queue %s.",
            PROCESSING_TASK_QUEUE,
            exc_info=True,
        )
        return 0


def processing_state_label(state):
    try:
        return BookCreationState(state).label
    except ValueError:
        return str(state or "")


def processing_display_url(url):
    return unquote(str(url or "").strip())


def processing_display_path(url):
    parsed = urlparse((url or "").strip())
    return unquote(parsed.path).strip("/") or parsed.netloc


def processing_request_details(request):
    progress = request.progress if isinstance(request.progress, dict) else {}
    checkpoint = str(progress.get("checkpoint") or "").strip()
    saved_at = str(progress.get("savedAt") or "").strip()
    if checkpoint and saved_at:
        return f"{checkpoint} ({saved_at})"
    if checkpoint:
        return checkpoint
    if request.error_message:
        return request.error_message
    if request.duplicate_confirmed:
        return "Confirmed duplicate"
    if request.is_confirmed_not_duplicate:
        return "Confirmed new"
    if request.is_resumed:
        return "Resumed from saved progress"
    return ""


def processing_linked_book(record, request=None):
    request_book = getattr(request, "linked_book", None) if request is not None else None
    if (
        request is not None
        and getattr(request, "linked_book_id", None)
        and request_book is not None
        and request_book.deleted_at is None
    ):
        return request_book

    record_book = getattr(record, "linked_book", None)
    if (
        getattr(record, "linked_book_id", None)
        and record_book is not None
        and record_book.deleted_at is None
    ):
        return record_book

    return None


def processing_row_payload(record, request=None, *, selectable=True):
    progress = request.progress if (request is not None and isinstance(request.progress, dict)) else {}
    linked_book = processing_linked_book(record, request)
    return {
        "id": str(request.id if request else record.id),
        "recordId": str(record.id),
        "requestId": str(request.id) if request else None,
        "title": record.name,
        "url": record.url,
        "displayUrl": processing_display_url(record.url),
        "displayPath": processing_display_path(record.url),
        "category": record.category,
        "writer": record.writer,
        "translator": record.translator,
        "publisher": record.publisher,
        "status": request.state if request else record.book_creation_state,
        "updatedAt": (
            request.updated_at.isoformat() if request else record.updated_at.isoformat()
        ),
        "selectable": bool(selectable),
        "progressCheckpoint": str(progress.get("checkpoint") or ""),
        "progressSavedAt": str(progress.get("savedAt") or ""),
        "errorMessage": request.error_message if request else "",
        "isResumed": bool(request.is_resumed) if request else False,
        "isConfirmedNotDuplicate": bool(request.is_confirmed_not_duplicate)
        if request
        else False,
        "linkedBookId": str(linked_book.id) if linked_book else None,
        "linkedBookSlug": linked_book.slug if linked_book else None,
        "duplicateOfRequestId": str(request.duplicate_of_request_id)
        if request and request.duplicate_of_request_id
        else None,
        "duplicateOfRecordId": str(request.duplicate_of_record_id)
        if request and request.duplicate_of_record_id
        else None,
        "duplicateConfirmed": bool(request.duplicate_confirmed) if request else False,
        "hasMultiPageToc": bool(request.has_multi_page_toc) if request else False,
        "sourceTocPageCount": int(request.source_toc_page_count) if request else 1,
        "fetchedTocPageCount": int(request.fetched_toc_page_count) if request else 1,
    }
