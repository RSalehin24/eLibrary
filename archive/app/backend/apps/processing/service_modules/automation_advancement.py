

def complete_catalog_automation(state, *, request_creation):
    created_count = int(request_creation.get("createdCount") or 0)
    unsupported_count = int(request_creation.get("unsupportedCount") or 0)
    finished_at = timezone.now()
    status_message = (
        f"Created {created_count} {'request' if created_count == 1 else 'requests'}."
    )
    if unsupported_count:
        status_message = (
            f"{status_message} Skipped {unsupported_count} unsupported "
            f"{'record' if unsupported_count == 1 else 'records'}."
        )
    update_automation_run_status(
        SYNC_RUN_MODE_CATALOG_AUTOMATION,
        status_message,
        last_run_at=finished_at,
    )
    current_sync_phase_state = catalog_phase_state(state, CATALOG_SYNC_PHASE)
    current_request_creation_phase_state = catalog_phase_state(
        state,
        CATALOG_REQUEST_CREATION_PHASE,
    )
    if current_sync_phase_state.get("status") == CATALOG_PHASE_STATUS_PAUSED:
        sync_phase_state = replace_catalog_phase_state(
            CATALOG_SYNC_PHASE,
            current_sync_phase_state,
        )
    else:
        sync_phase_state = replace_catalog_phase_state(
            CATALOG_SYNC_PHASE,
            current_sync_phase_state,
            status=CATALOG_PHASE_STATUS_COMPLETED,
            owner=(
                current_sync_phase_state.get("owner")
                or SYNC_RUN_MODE_CATALOG_AUTOMATION
            ),
            trigger_source=(
                current_sync_phase_state.get("triggerSource")
                or sync_trigger_source(state)
            ),
            saved_data={
                **_phase_saved_data(current_sync_phase_state.get("savedData")),
                "runMode": (
                    current_sync_phase_state.get("owner")
                    or SYNC_RUN_MODE_CATALOG_AUTOMATION
                ),
                "triggerSource": (
                    current_sync_phase_state.get("triggerSource")
                    or sync_trigger_source(state)
                ),
            },
            saved_at="",
        )
    request_creation_phase_state = _catalog_phase_state(
        CATALOG_REQUEST_CREATION_PHASE,
        status=CATALOG_PHASE_STATUS_COMPLETED,
        owner=SYNC_RUN_MODE_CATALOG_AUTOMATION,
        trigger_source=(
            current_request_creation_phase_state.get("triggerSource")
            or sync_trigger_source(state)
        ),
        base_sync_checkpoint_token=(
            current_request_creation_phase_state.get("baseSyncCheckpointToken")
            or request_creation_base_checkpoint_token(request_creation)
        ),
    )
    phase_states = {
        CATALOG_SYNC_PHASE: sync_phase_state,
        CATALOG_REQUEST_CREATION_PHASE: request_creation_phase_state,
    }
    return persist_catalog_phase_states(
        state,
        phase_states,
        message=(
            f"Automated catalog sync complete. Updated {state.updated_count}, "
            f"Skipped {state.skipped_count}, Added {state.appended_count}."
        ),
        update_fields=[
            "status",
            "progress",
            "task_id",
            "queue_name",
            "message",
            "page_index",
            "fetched_count",
            "skipped_count",
            "updated_count",
            "appended_count",
            "updated_at",
        ],
    )


def advance_catalog_request_creation_once(state):
    request_creation_phase_state = catalog_phase_state(
        state,
        CATALOG_REQUEST_CREATION_PHASE,
    )
    request_creation = catalog_request_creation_progress(state)
    request_creation_base_token = (
        str(request_creation_phase_state.get("baseSyncCheckpointToken") or "").strip()
        or request_creation_base_checkpoint_token(request_creation)
        or current_catalog_sync_checkpoint_token(state)
    )
    if not request_creation_matches_checkpoint(request_creation, request_creation_base_token):
        request_creation = {
            "baseCheckpointToken": request_creation_base_token,
            "lastRecordId": "",
            "processedCount": 0,
            "createdCount": 0,
            "unsupportedCount": 0,
        }
    batch = list(
        catalog_request_creation_queryset(
            after_record_id=str(request_creation.get("lastRecordId") or "").strip()
        )[:CATALOG_REQUEST_CREATION_BATCH_SIZE]
    )
    if not batch:
        return complete_catalog_automation(state, request_creation=request_creation)

    created_count = int(request_creation.get("createdCount") or 0)
    processed_count = int(request_creation.get("processedCount") or 0)
    unsupported_count = int(request_creation.get("unsupportedCount") or 0)
    last_record_id = str(request_creation.get("lastRecordId") or "").strip()
    for record in batch:
        last_record_id = str(record.id)
        processed_count += 1
        if not can_process_record_url(record.url):
            unsupported_count += 1
            logger.warning(
                "Skipping automation request creation for record %s because its URL is unsupported: %s",
                record.id,
                record.url,
            )
            continue
        latest_request = latest_request_for_record(record)
        if latest_request is None and record.book_creation_state == BookCreationState.NOT_CREATED:
            processing_request = create_request_for_record(
                record,
                origin=SubmissionOrigin.AUTOMATION,
            )
            if processing_request is not None:
                created_count += 1

    next_request_creation = {
        "baseCheckpointToken": request_creation_base_token,
        "lastRecordId": last_record_id,
        "processedCount": processed_count,
        "createdCount": created_count,
        "unsupportedCount": unsupported_count,
    }
    has_more_records = catalog_request_creation_queryset(
        after_record_id=last_record_id
    ).exists()
    latest_status = persisted_sync_status(state)
    if latest_status == ProcessingSyncStatus.PAUSING:
        if not has_more_records:
            return complete_catalog_automation(state, request_creation=next_request_creation)
        state.status = ProcessingSyncStatus.PAUSED
        state.progress = build_catalog_request_creation_progress(
            state,
            request_creation=next_request_creation,
            saved_at=timezone.now().isoformat(),
            trigger_source=sync_trigger_source(state),
            request_creation_phase_status=CATALOG_PHASE_STATUS_PAUSED,
            sync_phase_state=catalog_phase_state(state, CATALOG_SYNC_PHASE),
        )
        state.message = catalog_request_creation_pause_message(next_request_creation)
        update_automation_run_status(SYNC_RUN_MODE_CATALOG_AUTOMATION, state.message)
    elif latest_status != ProcessingSyncStatus.SYNCING:
        return ProcessingSyncState.objects.get(pk=state.pk)
    else:
        if not has_more_records:
            return complete_catalog_automation(state, request_creation=next_request_creation)
        state.progress = build_catalog_request_creation_progress(
            state,
            request_creation=next_request_creation,
            trigger_source=sync_trigger_source(state),
            request_creation_phase_status=CATALOG_PHASE_STATUS_RUNNING,
            sync_phase_state=catalog_phase_state(state, CATALOG_SYNC_PHASE),
        )
        state.message = catalog_request_creation_progress_message(next_request_creation)
    save_sync_state(state)
    return state


def incomplete_automation_pages(page_size=100):
    record_ids = [
        str(record.id)
        for record in unresolved_incomplete_records_queryset()
        .exclude(will_resolve_to_category="")
        .order_by("name", "id")
        .only("id", "category", "was_incomplete")
        if record.was_incomplete or category_is_incomplete(record.category)
    ]

    pages = []
    for index in range(0, len(record_ids), page_size):
        pages.append(record_ids[index : index + page_size])
    pages.append([])
    return pages


def unresolved_incomplete_records_queryset():
    return BookRecord.objects.filter(resolved_from_incomplete=False).filter(
        Q(was_incomplete=True) | incomplete_category_query()
    )


def uses_supported_source_url(url):
    try:
        normalize_source_url(url)
    except ValueError:
        return False
    return True


def should_use_live_incomplete_fetch():
    if not getattr(settings, "PROCESSING_USE_LIVE_SYNC", False):
        return False
    if settings.CELERY_TASK_ALWAYS_EAGER or "pytest" in sys.modules:
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False
    if not processing_workers_available():
        return False

    unresolved_urls = list(
        unresolved_incomplete_records_queryset().values_list("url", flat=True)
    )
    return not unresolved_urls or all(
        uses_supported_source_url(url) for url in unresolved_urls
    )


def incomplete_sync_remote_pages():
    if should_use_live_incomplete_fetch():
        try:
            return fetch_live_incomplete_remote_pages()
        except Exception:
            logger.warning(
                "Live incomplete catalog fetch failed; falling back to local incomplete snapshot.",
                exc_info=True,
            )
    return incomplete_automation_pages()


def preferred_incomplete_resolution_category(record):
    for candidate in (
        record.will_resolve_to_category,
        incomplete_resolution_category(
            getattr(record.source_catalog_entry, "raw_data", None),
        ),
        "" if category_is_incomplete(record.category) else record.category,
    ):
        value = str(candidate or "").strip()
        if value and not category_is_incomplete(value):
            return value
    return "Uncategorized"
