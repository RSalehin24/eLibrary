

def resolve_incomplete_records(record_ids):
    resolved = []
    published_domains = set()
    for record in BookRecord.objects.filter(pk__in=record_ids).select_related("source_catalog_entry"):
        if not (record.was_incomplete or category_is_incomplete(record.category)):
            continue
        before_snapshot = processing_record_snapshot(record)
        record.category = preferred_incomplete_resolution_category(record)
        record.was_incomplete = True
        record.resolved_from_incomplete = True
        record.book_creation_state = BookCreationRequestState.CREATED
        record.save(update_fields=["category", "was_incomplete", "resolved_from_incomplete", "book_creation_state", "updated_at"])
        latest_request = latest_request_for_record(record)
        if latest_request:
            previous_state = latest_request.state
            latest_request.state = BookCreationRequestState.CREATED
            latest_request.error_message = ""
            latest_request.progress = None
            latest_request.save(update_fields=["state", "error_message", "progress", "updated_at"])
            published_domains.update(
                processing_domains_for_request_change(
                    previous_state,
                    BookCreationRequestState.CREATED,
                    record=record,
                )
            )
        else:
            BookCreationRequest.objects.create(
                id=next_request_id(request_id_for_record(record)),
                book_record=record,
                state=BookCreationRequestState.CREATED,
                origin=SubmissionOrigin.AUTOMATION,
            )
            published_domains.update(
                processing_domains_for_request_change(
                    None,
                    BookCreationRequestState.CREATED,
                    record=record,
                )
            )
        published_domains.update(
            processing_domains_for_record_change(
                before_snapshot,
                processing_record_snapshot(record),
                current_request_state=BookCreationRequestState.CREATED,
            )
        )
        resolved.append(record)
    if published_domains:
        publish_processing_ui_domains(published_domains)
    return resolved


def complete_incomplete_automation(state, *, resolved_count=0):
    finished_at = timezone.now()
    update_automation_run_status(
        SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
        f"Updated {resolved_count} {'book' if resolved_count == 1 else 'books'}.",
        last_run_at=finished_at,
    )
    return finalize_sync(
        state,
        message=(
            f"Incomplete catalog sync complete. Updated {resolved_count} "
            f"{'book' if resolved_count == 1 else 'books'}."
        ),
    )


def incomplete_remote_urls(remote_pages):
    urls = set()
    for page in catalog_remote_pages(remote_pages):
        for item in page:
            url = str(item.get("url") or "").strip()
            if not url:
                continue
            try:
                urls.add(normalize_source_url(url))
            except ValueError:
                urls.add(url)
    return urls


def stale_incomplete_record_ids(remote_pages):
    current_urls = incomplete_remote_urls(remote_pages)
    stale_ids = []
    for record_id, url in unresolved_incomplete_records_queryset().values_list("id", "url"):
        normalized_url = str(url or "").strip()
        try:
            normalized_url = normalize_source_url(normalized_url)
        except ValueError:
            pass
        if normalized_url not in current_urls:
            stale_ids.append(record_id)
    return stale_ids


def complete_live_incomplete_sync(state):
    resolved = resolve_incomplete_records(stale_incomplete_record_ids(state.remote_pages))
    state.updated_count = len(resolved)
    save_sync_state(state, update_fields=["updated_count", "updated_at"])
    return complete_incomplete_automation(state, resolved_count=len(resolved))


def advance_live_incomplete_sync_once(state):
    resolver = TitleResolver(session=create_session_with_retries())
    seen_urls = incomplete_remote_urls(state.remote_pages)
    page_signatures = {
        tuple(item.get("url") for item in page[:5] if item.get("url"))
        for page in catalog_remote_pages(state.remote_pages)
        if page
    }

    page_number = state.page_index + 1
    page = fetch_live_incomplete_page(resolver, page_number)
    unique_page = []
    for item in page:
        source_url = item.get("url")
        if not source_url or source_url in seen_urls:
            continue
        seen_urls.add(source_url)
        unique_page.append(item)

    signature = tuple(item["url"] for item in unique_page[:5])
    if not unique_page or (signature and signature in page_signatures):
        return complete_live_incomplete_sync(state)

    state.remote_pages = [*catalog_remote_pages(state.remote_pages), unique_page]
    result = upsert_remote_records(unique_page)
    state.fetched_count += len(unique_page)
    state.skipped_count += result["skipped_count"]
    state.appended_count += result["appended_count"]
    state.page_index += 1

    latest_status = persisted_sync_status(state)
    if latest_status == ProcessingSyncStatus.PAUSING:
        state.status = ProcessingSyncStatus.PAUSED
        state.progress = build_sync_progress(
            SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            next_page_index=state.page_index,
            fetched_count=state.fetched_count,
            saved_at=timezone.now().isoformat(),
            live_fetch=True,
            trigger_source=sync_trigger_source(state),
        )
        state.message = (
            f"Saved progress for {state.fetched_count} "
            f"{'record' if state.fetched_count == 1 else 'records'} before pausing."
        )
        update_automation_run_status(SYNC_RUN_MODE_INCOMPLETE_AUTOMATION, state.message)
    elif latest_status != ProcessingSyncStatus.SYNCING:
        return ProcessingSyncState.objects.get(pk=state.pk)
    else:
        state.progress = build_sync_progress(
            SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            next_page_index=state.page_index,
            fetched_count=state.fetched_count,
            live_fetch=True,
            trigger_source=sync_trigger_source(state),
        )
        state.message = sync_progress_message(
            SYNC_RUN_MODE_INCOMPLETE_AUTOMATION,
            state.fetched_count,
        )
    save_sync_state(state)
    return state


def advance_catalog_sync_once(state, run_mode):
    page = state.remote_pages[state.page_index] if state.page_index < len(state.remote_pages) else []
    if not page:
        if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION:
            return begin_catalog_request_creation(state)
        return finalize_catalog_sync(state, run_mode=run_mode)

    result = upsert_remote_records(page)
    state.fetched_count += len(page)
    state.skipped_count += result["skipped_count"]
    state.updated_count += result["updated_count"]
    state.appended_count += result["appended_count"]
    state.page_index += 1
    next_page = state.remote_pages[state.page_index] if state.page_index < len(state.remote_pages) else []
    session_id = sync_saved_data(state).get("sessionId") or ""
    request_creation_phase_state = catalog_phase_state(
        state,
        CATALOG_REQUEST_CREATION_PHASE,
    )
    latest_status = persisted_sync_status(state)
    if latest_status == ProcessingSyncStatus.PAUSING:
        state.status = ProcessingSyncStatus.PAUSED
        state.progress = build_catalog_sync_progress(
            state,
            run_mode,
            next_page_index=state.page_index,
            fetched_count=state.fetched_count,
            saved_at=timezone.now().isoformat(),
            live_fetch=sync_uses_live_fetch(state),
            trigger_source=sync_trigger_source(state),
            session_id=session_id,
            sync_phase_status=CATALOG_PHASE_STATUS_PAUSED,
            request_creation_phase_state=request_creation_phase_state,
        )
        state.message = f"Sync progress saved. {catalog_record_total_message()}"
        update_automation_run_status(run_mode, state.message)
    elif latest_status != ProcessingSyncStatus.SYNCING:
        return ProcessingSyncState.objects.get(pk=state.pk)
    elif not next_page:
        if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION:
            return begin_catalog_request_creation(state)
        return finalize_catalog_sync(state, run_mode=run_mode)
    else:
        state.progress = build_catalog_sync_progress(
            state,
            run_mode,
            next_page_index=state.page_index,
            fetched_count=state.fetched_count,
            live_fetch=sync_uses_live_fetch(state),
            trigger_source=sync_trigger_source(state),
            session_id=session_id,
            sync_phase_status=CATALOG_PHASE_STATUS_RUNNING,
            request_creation_phase_state=request_creation_phase_state,
        )
        state.message = sync_progress_message(run_mode, state.fetched_count)
    save_sync_state(state)
    return state


def advance_catalog_processing_once(state, run_mode):
    if sync_phase(state) == CATALOG_REQUEST_CREATION_PHASE:
        return advance_catalog_request_creation_once(state)
    return advance_catalog_sync_once(state, run_mode)
