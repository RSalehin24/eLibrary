

def sync_state_task_payload(state):
    progress = (
        sync_progress_payload(state)
        if isinstance(state.progress, dict)
        else None
    )
    return {
        "singleton_key": state.singleton_key,
        "status": state.status,
        "progress": progress,
        "remote_pages": state.remote_pages,
        "page_index": state.page_index,
        "fetched_count": state.fetched_count,
        "skipped_count": state.skipped_count,
        "updated_count": state.updated_count,
        "appended_count": state.appended_count,
        "message": state.message,
        "run_mode": sync_run_mode(state),
    }

def processing_sync_checkpoint_key(sync_key):
    return f"{PROCESSING_SYNC_CHECKPOINT_KEY_PREFIX}:{sync_key}"


def processing_checkpoint_redis_url():
    return str(
        getattr(settings, "PROCESSING_CHECKPOINT_REDIS_URL", "")
        or settings.CELERY_BROKER_URL
        or ""
    ).strip()


def processing_checkpoint_client():
    redis_url = processing_checkpoint_redis_url()
    if not redis_url:
        return None

    if (
        PROCESSING_CHECKPOINT_REDIS["client"] is not None
        and PROCESSING_CHECKPOINT_REDIS["url"] == redis_url
        and not PROCESSING_CHECKPOINT_REDIS["disabled"]
    ):
        return PROCESSING_CHECKPOINT_REDIS["client"]

    if (
        PROCESSING_CHECKPOINT_REDIS["disabled"]
        and PROCESSING_CHECKPOINT_REDIS["url"] == redis_url
    ):
        return None

    try:
        client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=0.5,
            socket_timeout=0.5,
        )
        PROCESSING_CHECKPOINT_REDIS.update(
            {
                "url": redis_url,
                "client": client,
                "disabled": False,
            }
        )
        return client
    except Exception:
        logger.debug(
            "Processing checkpoint Redis client initialization failed.",
            exc_info=True,
        )
        PROCESSING_CHECKPOINT_REDIS.update(
            {
                "url": redis_url,
                "client": None,
                "disabled": True,
            }
        )
        return None


def processing_checkpoint_payload(state):
    progress = (
        sync_progress_payload(state)
        if isinstance(state.progress, dict)
        else None
    )
    if not progress:
        return None

    return {
        "scope": state.singleton_key,
        "status": state.status,
        "runMode": sync_run_mode(state),
        "triggerSource": sync_trigger_source(state),
        "pageIndex": state.page_index,
        "fetchedCount": state.fetched_count,
        "skippedCount": state.skipped_count,
        "updatedCount": state.updated_count,
        "appendedCount": state.appended_count,
        "message": state.message,
        "progress": progress,
        "updatedAt": state.updated_at.isoformat() if state.updated_at else "",
    }


def clear_processing_checkpoint_mirror(sync_key):
    client = processing_checkpoint_client()
    if client is None:
        return False

    try:
        client.delete(processing_sync_checkpoint_key(sync_key))
        return True
    except RedisError:
        logger.debug(
            "Processing checkpoint Redis delete failed for %s.",
            sync_key,
            exc_info=True,
        )
        return False


def mirror_processing_checkpoint(state):
    client = processing_checkpoint_client()
    if client is None:
        return False

    payload = processing_checkpoint_payload(state)
    checkpoint_key = processing_sync_checkpoint_key(state.singleton_key)
    try:
        if payload is None:
            client.delete(checkpoint_key)
        else:
            client.set(checkpoint_key, json.dumps(payload))
        return True
    except RedisError:
        logger.debug(
            "Processing checkpoint Redis write failed for %s.",
            state.singleton_key,
            exc_info=True,
        )
        return False


def sync_checkpoint_progress(state):
    progress = (
        sync_progress_payload(state)
        if isinstance(state.progress, dict)
        else None
    )
    if progress:
        mirror_processing_checkpoint(state)
    else:
        clear_processing_checkpoint_mirror(state.singleton_key)
    return progress


def save_sync_state(state, *, update_fields=None):
    if state.pk is None or update_fields is None:
        state.save()
    else:
        unique_fields = list(dict.fromkeys(update_fields))
        state.save(update_fields=unique_fields)
    sync_checkpoint_progress(state)
    publish_processing_ui_domains(processing_domains_for_sync_state(state))
    return state


def should_run_processing_jobs_inline():
    return bool(
        settings.CELERY_TASK_ALWAYS_EAGER
        or getattr(settings, "PROCESSING_INLINE_PIPELINE_ADVANCE", False)
    )


def processing_workers_available(queue_name=PROCESSING_TASK_QUEUE):
    if should_run_processing_jobs_inline():
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return False

    checked_at = PROCESSING_WORKER_AVAILABILITY["checked_at"]
    available = PROCESSING_WORKER_AVAILABILITY["available"]
    now = monotonic()
    if available is not None and (now - checked_at) < PROCESSING_WORKER_CACHE_SECONDS:
        return available

    detected = False
    try:
        inspector = celery_app.control.inspect(timeout=0.5)
        active_queues = inspector.active_queues() or {}
        detected = any(
            any((queue or {}).get("name") == queue_name for queue in (queues or []))
            for queues in active_queues.values()
        )
    except Exception:
        logger.debug(
            "Processing worker availability check failed; assuming manual progression.",
            exc_info=True,
        )

    PROCESSING_WORKER_AVAILABILITY["checked_at"] = now
    PROCESSING_WORKER_AVAILABILITY["available"] = detected
    return detected


def should_enqueue_processing_work():
    if should_run_processing_jobs_inline():
        return False
    if os.environ.get("PYTEST_CURRENT_TEST"):
        return processing_workers_available()
    return True


def should_enqueue_processing_sync_work():
    return should_enqueue_processing_work() and processing_workers_available()


def should_manually_advance_processing_work():
    return not should_run_processing_jobs_inline() and not processing_workers_available()


def should_skip_processing_metadata_duplicate_check():
    return bool(
        getattr(settings, "PROCESSING_SKIP_METADATA_DUPLICATE_CHECK", True)
    )


def allow_processing_remote_page_payloads():
    return bool(
        getattr(settings, "PROCESSING_ALLOW_REMOTE_PAGE_PAYLOADS", False)
        or "pytest" in sys.modules
        or os.environ.get("PYTEST_CURRENT_TEST")
    )


def can_process_record_url(url):
    return allow_processing_remote_page_payloads() or uses_supported_source_url(url)


def sync_uses_live_fetch(state):
    saved_data = sync_saved_data(state)
    return bool(saved_data.get("liveFetch"))


def sync_run_label(run_mode):
    if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION:
        return "Automated catalog sync"
    if run_mode == SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        return "Incomplete catalog sync"
    return "Catalog sync"


def sync_start_message(run_mode):
    if run_mode == SYNC_RUN_MODE_CATALOG_AUTOMATION:
        return "Automated catalog sync is running."
    if run_mode == SYNC_RUN_MODE_INCOMPLETE_AUTOMATION:
        return "Incomplete catalog sync is running."
    return "Syncing catalog records."
