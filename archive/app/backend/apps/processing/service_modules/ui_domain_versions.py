

@contextmanager
def collect_processing_ui_version_updates():
    collector = PROCESSING_UI_VERSION_COLLECTOR.get()
    if collector is not None:
        yield collector
        return

    collector = {}
    token = PROCESSING_UI_VERSION_COLLECTOR.set(collector)
    try:
        yield collector
    finally:
        PROCESSING_UI_VERSION_COLLECTOR.reset(token)


def _merge_processing_ui_versions(collector, versions):
    if collector is None:
        return collector
    for domain, version in (versions or {}).items():
        normalized_version = int(version or 0)
        if normalized_version <= int(collector.get(domain, 0)):
            continue
        collector[domain] = normalized_version
    return collector


def _plan_processing_ui_versions(collector, domains):
    if collector is None or not domains:
        return collector

    current_versions = processing_ui_versions_map(domains=domains)
    for domain in domains:
        collector[domain] = max(
            int(current_versions.get(domain, 0)),
            int(collector.get(domain, 0)),
        ) + 1
    return collector


def _ordered_processing_ui_domains(domains):
    return sorted({domain for domain in domains or [] if domain in PROCESSING_CARD_KEYS})


def _ensure_processing_ui_domain_versions(domains):
    if not domains:
        return
    ProcessingUiDomainVersion.objects.bulk_create(
        [
            ProcessingUiDomainVersion(domain=domain, version=0)
            for domain in domains
        ],
        ignore_conflicts=True,
    )


def _bump_processing_ui_domains(domains):
    ordered_domains = _ordered_processing_ui_domains(domains)
    _ensure_processing_ui_domain_versions(ordered_domains)

    next_versions = {}
    version_rows = (
        ProcessingUiDomainVersion.objects.select_for_update()
        .filter(domain__in=ordered_domains)
        .order_by("domain")
    )
    for version_row in version_rows:
        version_row.version = int(version_row.version) + 1
        version_row.save(update_fields=["version", "updated_at"])
        next_versions[version_row.domain] = int(version_row.version)
    return next_versions


def processing_shared_projection_keys_for_domains(domains):
    projection_keys = set()
    for domain in domains or []:
        projection_keys.update(
            PROCESSING_SHARED_PROJECTION_DEPENDENCIES.get(domain, set())
        )
    return sorted(projection_keys)


def publish_processing_ui_domains(domains):
    normalized_domains = _ordered_processing_ui_domains(domains)
    if not normalized_domains:
        return

    projection_keys = processing_shared_projection_keys_for_domains(normalized_domains)
    collector = PROCESSING_UI_VERSION_COLLECTOR.get()
    _plan_processing_ui_versions(collector, normalized_domains)

    def commit():
        if projection_keys:
            rebuild_processing_ui_state(keys=projection_keys)
        with transaction.atomic():
            next_versions = _bump_processing_ui_domains(normalized_domains)
        _merge_processing_ui_versions(collector, next_versions)

    transaction.on_commit(commit)


def processing_domains_for_request_change(
    before_state,
    after_state,
    *,
    record=None,
):
    domains = {
        PROCESSING_CARD_CATALOG_OVERVIEW,
        PROCESSING_CARD_CATALOG_RECORDS,
    }

    before_card = processing_request_card_for_state(before_state)
    after_card = processing_request_card_for_state(after_state)
    if before_card:
        domains.add(before_card)
    if after_card:
        domains.add(after_card)

    before_overview = processing_overview_card_for_state(before_state)
    after_overview = processing_overview_card_for_state(after_state)
    if before_overview:
        domains.add(before_overview)
    if after_overview:
        domains.add(after_overview)

    # The multi-page TOC page surfaces requests across every state, so refresh it
    # whenever any request transitions.
    domains.add(PROCESSING_CARD_MULTIPAGE_RECORDS)

    if record is not None:
        if processing_record_is_incomplete(record):
            domains.update(
                {
                    PROCESSING_CARD_INCOMPLETE_OVERVIEW,
                    PROCESSING_CARD_INCOMPLETE_RECORDS,
                }
            )
        if record.was_incomplete and record.resolved_from_incomplete:
            domains.update(
                {
                    PROCESSING_CARD_INCOMPLETE_OVERVIEW,
                    PROCESSING_CARD_INCOMPLETE_COMPLETED,
                }
            )

    return domains


def processing_domains_for_record_change(
    before_snapshot,
    after_snapshot,
    *,
    current_request_state=None,
):
    domains = {
        PROCESSING_CARD_CATALOG_OVERVIEW,
        PROCESSING_CARD_CATALOG_RECORDS,
    }
    if current_request_state:
        current_card = processing_request_card_for_state(current_request_state)
        if current_card:
            domains.add(current_card)

    if processing_record_is_incomplete(before_snapshot) or processing_record_is_incomplete(
        after_snapshot
    ):
        domains.update(
            {
                PROCESSING_CARD_INCOMPLETE_OVERVIEW,
                PROCESSING_CARD_INCOMPLETE_RECORDS,
            }
        )

    after_resolved = bool(after_snapshot and after_snapshot.get("resolved_from_incomplete"))
    before_resolved = bool(
        before_snapshot and before_snapshot.get("resolved_from_incomplete")
    )
    if after_resolved or before_resolved:
        domains.update(
            {
                PROCESSING_CARD_INCOMPLETE_OVERVIEW,
                PROCESSING_CARD_INCOMPLETE_COMPLETED,
            }
        )

    return domains


def processing_domains_for_sync_state(state):
    sync_key = (
        state.singleton_key
        if isinstance(state, ProcessingSyncState)
        else str(state or "").strip().lower()
    )
    if sync_key == PROCESSING_SYNC_KEY_INCOMPLETE:
        return {PROCESSING_CARD_INCOMPLETE_AUTOMATION}
    return {PROCESSING_CARD_CATALOG_SYNC}


def processing_domains_for_automation(kind):
    if kind == ProcessingAutomationKind.INCOMPLETE:
        return {PROCESSING_CARD_INCOMPLETE_AUTOMATION}
    return {PROCESSING_CARD_CATALOG_AUTOMATION}
