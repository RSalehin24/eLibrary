def create_catalog_state(self, admin: User):
    CatalogAutomationSettings.objects.update_or_create(
        singleton_key="default",
        defaults={
            "enabled": False,
            "daily_run_time": time(2, 0),
            "frequency": "daily",
            "mode": "pending",
            "refresh_max_pages": 80,
            "updated_by": admin,
        },
    )
    SourceCatalogRefreshState.objects.update_or_create(
        singleton_key="default",
        defaults={
            "status": SourceCatalogRefreshStatus.IDLE,
            "max_pages": 80,
            "requested_by": admin,
        },
    )
    for entry in CATALOG_ENTRIES:
        SourceCatalogEntry.objects.create(
            source_url=entry["source_url"],
            title=entry["title"],
            author_line=entry["author_line"],
            normalized_title=normalize_catalog_text(entry["title"]),
            normalized_display=normalize_catalog_text(
                f"{entry['title']} {entry['author_line']}"
            ),
            raw_data={
                "title": entry["title"],
                "author": entry["author_line"],
                "category": entry["category"],
            },
        )
    CatalogCurationRun.objects.create(
        trigger=CatalogCurationTrigger.SCHEDULED,
        mode=CatalogCurationMode.PENDING,
        status=JobStatus.CANCELLED,
        refresh_catalog=True,
        refresh_max_pages=12,
        requested_by=admin,
        last_error="Seeded scheduled run stopped.",
        summary=SCHEDULED_RUN_ACTIVE_SUMMARY,
    )
    CatalogCurationRun.objects.create(
        trigger=CatalogCurationTrigger.SCHEDULED,
        mode=CatalogCurationMode.ALL,
        status=JobStatus.FAILED,
        refresh_catalog=True,
        refresh_max_pages=24,
        requested_by=admin,
        last_error="Seeded scheduled automation failure.",
        summary=SCHEDULED_RUN_FAILED_SUMMARY,
    )
def create_processing_state(
    self,
    *,
    BookRecord,
    BookCreationRequest,
    BookCreationRequestState,
    sync_record_state,
):
    created_record, _ = BookRecord.objects.update_or_create(
        url=seed_source_url("seeded-created-flow-record"),
        defaults={
            "name": "000 E2E Seeded Created Flow Record",
            "category": DEFAULT_CATEGORY,
            "writer": DEFAULT_WRITER,
            "translator": "",
            "composer": "",
            "publisher": "",
            "linked_book": None,
            "was_incomplete": False,
            "resolved_from_incomplete": False,
            "will_resolve_to_category": "",
            "is_duplicate": False,
            "duplicate_of_record": None,
            "source_catalog_entry": None,
        },
    )
    created_request = BookCreationRequest.objects.create(
        book_record=created_record,
        state=BookCreationRequestState.CREATED,
        origin=SubmissionOrigin.CURATION,
    )
    sync_record_state(created_record)

    duplicate_record, _ = BookRecord.objects.update_or_create(
        url=seed_source_url("seeded-duplicate-flow-record"),
        defaults={
            "name": "000 E2E Seeded Duplicate Flow Record",
            "category": DEFAULT_CATEGORY,
            "writer": DEFAULT_WRITER,
            "translator": "",
            "composer": "",
            "publisher": "",
            "linked_book": None,
            "was_incomplete": False,
            "resolved_from_incomplete": False,
            "will_resolve_to_category": "",
            "is_duplicate": True,
            "duplicate_of_record": created_record,
            "source_catalog_entry": None,
        },
    )
    BookCreationRequest.objects.create(
        book_record=duplicate_record,
        state=BookCreationRequestState.DUPLICATE,
        origin=SubmissionOrigin.CURATION,
        duplicate_of_request=created_request,
        duplicate_of_record=created_record,
    )
    sync_record_state(duplicate_record)
