

def is_valid_uuid_string(value):
    try:
        uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError):
        return False
    return True


def upsert_remote_records(records):
    skipped_count = 0
    updated_count = 0
    appended_count = 0
    published_domains = set()

    for raw_record in records:
        data = normalize_remote_record(raw_record)
        if not data["url"]:
            continue

        source_entry_filters = Q(source_url=data["url"])
        if is_valid_uuid_string(data["id"]):
            source_entry_filters |= Q(pk=data["id"])
        source_entry = SourceCatalogEntry.objects.filter(source_entry_filters).order_by("-updated_at").first()
        linked_book = linked_book_for_remote_url(data["url"])
        desired_state = (
            data["bookCreationState"]
            if data["bookCreationState"] in BookCreationState.values
            else BookCreationState.CREATED if linked_book else BookCreationState.NOT_CREATED
        )
        defaults = {
            "name": data["name"],
            "url": data["url"],
            "category": data["category"],
            "writer": data["writer"],
            "translator": data["translator"],
            "composer": data["composer"],
            "publisher": data["publisher"],
            "book_creation_state": desired_state,
            "linked_book": linked_book,
            "source_catalog_entry": source_entry,
            "was_incomplete": data["wasIncomplete"],
            "resolved_from_incomplete": data["resolvedFromIncomplete"],
            "will_resolve_to_category": data["willResolveToCategory"],
        }

        record = (
            BookRecord.objects.select_related("linked_book")
            .filter(Q(pk=data["id"]) | Q(url=data["url"]))
            .order_by("id")
            .first()
        )
        before_snapshot = processing_record_snapshot(record)
        if record is None:
            preferred_id = data["id"] or None
            create_kwargs = dict(defaults)
            if preferred_id and not BookRecord.objects.filter(pk=preferred_id).exists():
                create_kwargs["id"] = preferred_id
            try:
                record = BookRecord.objects.create(**create_kwargs)
                sync_record_state(record)
                published_domains.update(
                    processing_domains_for_record_change(
                        None,
                        processing_record_snapshot(record),
                    )
                )
                appended_count += 1
                continue
            except IntegrityError:
                record = (
                    BookRecord.objects.select_related("linked_book")
                    .filter(Q(pk=data["id"]) | Q(url=data["url"]))
                    .order_by("id")
                    .first()
                )
                if record is None:
                    raise

        changed_fields = [
            field_name
            for field_name, value in defaults.items()
            if getattr(record, field_name) != value
        ]
        if changed_fields:
            for field_name in changed_fields:
                setattr(record, field_name, defaults[field_name])
            record.save(update_fields=[*changed_fields, "updated_at"])
            updated_count += 1
        else:
            skipped_count += 1

        sync_record_state(record)
        after_snapshot = processing_record_snapshot(record)
        if before_snapshot != after_snapshot:
            published_domains.update(
                processing_domains_for_record_change(
                    before_snapshot,
                    after_snapshot,
                )
            )

    if published_domains:
        publish_processing_ui_domains(published_domains)
    return {
        "skipped_count": skipped_count,
        "updated_count": updated_count,
        "appended_count": appended_count,
    }


def source_catalog_remote_pages(page_size=100):
    entries = SourceCatalogEntry.objects.order_by("title", "id")
    pages = []
    current_page = []
    for entry in entries.iterator(chunk_size=page_size):
        current_page.append(source_catalog_entry_payload(entry))
        if len(current_page) >= page_size:
            pages.append(current_page)
            current_page = []
    if current_page:
        pages.append(current_page)
    pages.append([])
    return pages


def reconcile_remote_pages(remote_pages):
    remote_pages = remote_pages if isinstance(remote_pages, list) else []
    fetched_count = 0
    skipped_count = 0
    updated_count = 0
    appended_count = 0
    page_index = 0
    completed = False

    for page in remote_pages:
        if not page:
            completed = True
            break

        result = upsert_remote_records(page)
        fetched_count += len(page)
        skipped_count += result["skipped_count"]
        updated_count += result["updated_count"]
        appended_count += result["appended_count"]
        page_index += 1

    if remote_pages and not completed:
        page_index = len(remote_pages)

    return {
        "fetched_count": fetched_count,
        "skipped_count": skipped_count,
        "updated_count": updated_count,
        "appended_count": appended_count,
        "page_index": page_index,
        "completed": completed or not remote_pages,
    }


def should_use_live_catalog_fetch(remote_pages, run_mode):
    return (
        bool(getattr(settings, "PROCESSING_USE_LIVE_SYNC", False))
        and not settings.CELERY_TASK_ALWAYS_EAGER
        and "pytest" not in sys.modules
        and not os.environ.get("PYTEST_CURRENT_TEST")
        and not remote_pages
        and run_mode in {SYNC_RUN_MODE_MANUAL, SYNC_RUN_MODE_CATALOG_AUTOMATION}
        and processing_workers_available()
    )


def dispatch_sync_task(sync_state, *, force=False):
    from .tasks import run_processing_sync_task

    sync_state.refresh_from_db(fields=["status", "task_id", "queue_name", "updated_at"])
    if sync_state.status not in SYNC_ACTIVE_STATUSES:
        return sync_state
    if not force and sync_state.task_id:
        return sync_state

    assigned_task_id = str(uuid4())
    sync_state.task_id = assigned_task_id
    sync_state.queue_name = PROCESSING_TASK_QUEUE
    sync_state.last_error = ""
    save_sync_state(
        sync_state,
        update_fields=["task_id", "queue_name", "last_error", "updated_at"],
    )

    try:
        async_result = run_processing_sync_task.apply_async(
            args=[sync_state.singleton_key],
            task_id=assigned_task_id,
            queue=PROCESSING_TASK_QUEUE,
        )
        dispatched_task_id = getattr(async_result, "id", assigned_task_id) or assigned_task_id
        if dispatched_task_id != assigned_task_id:
            sync_state.task_id = dispatched_task_id
            save_sync_state(sync_state, update_fields=["task_id", "updated_at"])
    except Exception as exc:
        logger.warning("Processing sync task dispatch failed.", exc_info=True)
        sync_state.task_id = ""
        sync_state.queue_name = "inline-fallback"
        sync_state.last_error = str(exc)
        save_sync_state(
            sync_state,
            update_fields=["task_id", "queue_name", "last_error", "updated_at"],
        )
        run_processing_sync_until_blocked(
            singleton_key=sync_state.singleton_key,
            task_id="",
        )
    return sync_state



def incomplete_catalog_page_url(page_number):
    if page_number <= 1:
        return INCOMPLETE_CATALOG_URL
    return urljoin(INCOMPLETE_CATALOG_URL, f"page/{page_number}/")


def refresh_catalog_parallel(concurrency=None):
    from apps.ingestion.pipeline.scraper_support.network import create_session_with_retries

    if concurrency is None:
        concurrency = getattr(settings, "CELERY_PROCESSING_CONCURRENCY", 5)

    stop_flag = threading.Event()
    page_lock = threading.Lock()
    seen_lock = threading.Lock()
    count_lock = threading.Lock()
    next_page = 1
    seen_urls = set()
    total_appended = 0
    total_updated = 0

    def worker():
        nonlocal next_page, total_appended, total_updated

        while not stop_flag.is_set():
            with page_lock:
                if stop_flag.is_set():
                    return
                page_number = next_page
                next_page += 1

            session = create_session_with_retries()
            resolver = TitleResolver(session=session)

            try:
                response = get_with_host_fallback(
                    resolver.session,
                    CATALOG_URL,
                    params=resolver.archive_query_params(page_number=page_number),
                    timeout=30,
                )
                response.raise_for_status()
                soup = BeautifulSoup(response.text, "html.parser")
                entries = resolver.parse_catalog_page(soup)
            except Exception:
                continue

            if not entries:
                stop_flag.set()
                return

            local_appended = 0
            local_updated = 0
            for entry in entries:
                if stop_flag.is_set():
                    return

                with seen_lock:
                    if entry["source_url"] in seen_urls:
                        continue
                    seen_urls.add(entry["source_url"])

                try:
                    metadata = fetch_source_page_metadata(
                        entry["source_url"], session=session
                    )
                    stored_entry = upsert_source_catalog_entry(metadata)
                    payload = source_catalog_entry_payload(stored_entry)
                    result = upsert_remote_records([payload])
                    local_appended += result["appended_count"]
                    local_updated += result["updated_count"]
                except Exception:
                    continue

            with count_lock:
                total_appended += local_appended
                total_updated += local_updated

    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker) for _ in range(concurrency)]
        for future in futures:
            future.result()

    return {
        "appended_count": total_appended,
        "updated_count": total_updated,
        "total": total_appended + total_updated,
    }
