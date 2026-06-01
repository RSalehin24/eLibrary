

def request_processing_rows(states, *, predicate=None):
    queryset = (
        BookCreationRequest.objects.filter(state__in=states)
        .select_related("book_record", "linked_book", "book_record__linked_book")
        .order_by("-updated_at", "-created_at", "id")
    )
    rows = []
    for processing_request in queryset:
        record = processing_request.book_record
        if predicate and not predicate(processing_request, record):
            continue
        rows.append(processing_row_payload(record, processing_request))
    return rows


def incomplete_record_rows():
    queryset = (
        BookRecord.objects.select_related("linked_book")
        .prefetch_related(processing_request_prefetch())
        .filter(resolved_from_incomplete=False)
        .filter(Q(was_incomplete=True) | incomplete_category_query())
        .order_by("name", "id")
    )
    rows = []
    for record in queryset:
        latest_request = latest_request_for_record(record)
        rows.append(
            processing_row_payload(
                record,
                latest_request,
                selectable=False,
            )
        )
    return rows


def incomplete_completed_rows():
    return request_processing_rows(
        {BookCreationRequestState.CREATED},
        predicate=lambda _request, record: bool(
            record.was_incomplete and record.resolved_from_incomplete
        ),
    )


def multipage_toc_rows():
    queryset = (
        BookCreationRequest.objects.filter(has_multi_page_toc=True)
        .select_related("book_record", "linked_book", "book_record__linked_book")
        .order_by("-updated_at", "-created_at", "id")
    )
    return [
        processing_row_payload(processing_request.book_record, processing_request)
        for processing_request in queryset
    ]


def multipage_toc_summary():
    queryset = BookCreationRequest.objects.filter(has_multi_page_toc=True)
    return {
        "total": queryset.count(),
        "created": queryset.filter(state=BookCreationRequestState.CREATED).count(),
        "failed": queryset.filter(state=BookCreationRequestState.FAILED).count(),
        "processing": queryset.filter(
            state__in=(
                BookCreationRequestState.INITIAL,
                BookCreationRequestState.QUEUED,
                BookCreationRequestState.PROCESSING,
            )
        ).count(),
    }


PROCESSING_TABLE_BUILDERS = {
    "catalog-records": catalog_processing_rows,
    "incomplete-records": incomplete_record_rows,
    "incomplete-completed": incomplete_completed_rows,
    "multipage-records": multipage_toc_rows,
    **{
        card_id: (lambda states: lambda: request_processing_rows(states))(states)
        for card_id, states in PROCESSING_REQUEST_CARD_STATES.items()
    },
}


def processing_table_payload(
    card,
    *,
    query="",
    category="",
    status="",
    offset=0,
    limit=PROCESSING_TABLE_DEFAULT_LIMIT,
    include_facets=True,
):
    offset_value = max(0, int(offset or 0))
    limit_value = max(
        1,
        min(int(limit or PROCESSING_TABLE_DEFAULT_LIMIT), PROCESSING_TABLE_MAX_LIMIT),
    )
    query_value = str(query or "").strip()

    if card == "catalog-records":
        payload = build_processing_record_table_payload(
            order_catalog_records_queryset(
                annotate_record_processing_status(
                    BookRecord.objects.select_related("linked_book")
                    .prefetch_related(processing_request_prefetch())
                )
            ),
            query=query_value,
            category=category,
            status=status,
            offset=offset_value,
            limit=limit_value,
            include_facets=include_facets,
        )
        payload["version"] = processing_ui_versions_map(domains=[card]).get(card, 0)
        return payload

    if card == "incomplete-records":
        payload = build_processing_record_table_payload(
            annotate_record_processing_status(
                BookRecord.objects.select_related("linked_book")
                .prefetch_related(processing_request_prefetch())
                .filter(resolved_from_incomplete=False)
                .filter(Q(was_incomplete=True) | incomplete_category_query())
                .order_by("name", "id")
            ),
            query=query_value,
            category=category,
            status=status,
            offset=offset_value,
            limit=limit_value,
            selectable=False,
            include_facets=include_facets,
        )
        payload["version"] = processing_ui_versions_map(domains=[card]).get(card, 0)
        return payload

    if card == "incomplete-completed":
        payload = build_processing_request_table_payload(
            BookCreationRequest.objects.filter(state=BookCreationRequestState.CREATED)
            .filter(
                book_record__was_incomplete=True,
                book_record__resolved_from_incomplete=True,
            )
            .select_related("book_record", "linked_book", "book_record__linked_book")
            .defer(
                "linked_book__summary",
                "linked_book__raw_scraped_metadata",
                "linked_book__raw_scrape_payload",
                "linked_book__main_content_html",
                "linked_book__book_info_html",
                "linked_book__dedication_html",
                "linked_book__toc",
                "linked_book__content_items",
                "book_record__linked_book__summary",
                "book_record__linked_book__raw_scraped_metadata",
                "book_record__linked_book__raw_scrape_payload",
                "book_record__linked_book__main_content_html",
                "book_record__linked_book__book_info_html",
                "book_record__linked_book__dedication_html",
                "book_record__linked_book__toc",
                "book_record__linked_book__content_items",
            )
            .order_by("-updated_at", "-created_at", "id"),
            query=query_value,
            category=category,
            status=status,
            offset=offset_value,
            limit=limit_value,
            include_facets=include_facets,
        )
        payload["version"] = processing_ui_versions_map(domains=[card]).get(card, 0)
        return payload

    if card in PROCESSING_REQUEST_CARD_STATES:
        payload = build_processing_request_table_payload(
            BookCreationRequest.objects.filter(state__in=PROCESSING_REQUEST_CARD_STATES[card])
            .select_related("book_record", "linked_book", "book_record__linked_book")
            .defer(
                "linked_book__summary",
                "linked_book__raw_scraped_metadata",
                "linked_book__raw_scrape_payload",
                "linked_book__main_content_html",
                "linked_book__book_info_html",
                "linked_book__dedication_html",
                "linked_book__toc",
                "linked_book__content_items",
                "book_record__linked_book__summary",
                "book_record__linked_book__raw_scraped_metadata",
                "book_record__linked_book__raw_scrape_payload",
                "book_record__linked_book__main_content_html",
                "book_record__linked_book__book_info_html",
                "book_record__linked_book__dedication_html",
                "book_record__linked_book__toc",
                "book_record__linked_book__content_items",
            )
            .order_by("-updated_at", "-created_at", "id"),
            query=query_value,
            category=category,
            status=status,
            offset=offset_value,
            limit=limit_value,
            include_facets=include_facets,
        )
        payload["version"] = processing_ui_versions_map(domains=[card]).get(card, 0)
        return payload

    if card == "multipage-records":
        payload = build_processing_request_table_payload(
            BookCreationRequest.objects.filter(has_multi_page_toc=True)
            .select_related("book_record", "linked_book", "book_record__linked_book")
            .defer(
                "linked_book__summary",
                "linked_book__raw_scraped_metadata",
                "linked_book__raw_scrape_payload",
                "linked_book__main_content_html",
                "linked_book__book_info_html",
                "linked_book__dedication_html",
                "linked_book__toc",
                "linked_book__content_items",
                "book_record__linked_book__summary",
                "book_record__linked_book__raw_scraped_metadata",
                "book_record__linked_book__raw_scrape_payload",
                "book_record__linked_book__main_content_html",
                "book_record__linked_book__book_info_html",
                "book_record__linked_book__dedication_html",
                "book_record__linked_book__toc",
                "book_record__linked_book__content_items",
            )
            .order_by("-updated_at", "-created_at", "id"),
            query=query_value,
            category=category,
            status=status,
            offset=offset_value,
            limit=limit_value,
            include_facets=include_facets,
        )
        payload["summary"] = multipage_toc_summary()
        payload["version"] = processing_ui_versions_map(domains=[card]).get(card, 0)
        return payload

    raise KeyError(card)


def processing_request_counts():
    return {
        state: BookCreationRequest.objects.filter(state=state).count()
        for state in BookCreationRequestState.values
    }


def processing_incomplete_counts():
    incomplete_records = (
        BookRecord.objects.filter(resolved_from_incomplete=False)
        .filter(Q(was_incomplete=True) | incomplete_category_query())
        .count()
    )
    resolved_records = BookRecord.objects.filter(
        was_incomplete=True,
        resolved_from_incomplete=True,
    ).count()
    return {
        "incomplete": incomplete_records,
        "resolved": resolved_records,
    }


def processing_summary_payload():
    request_counts = processing_request_counts()
    latest_failed_message = (
        BookCreationRequest.objects.filter(state=BookCreationRequestState.FAILED)
        .exclude(error_message="")
        .order_by("-updated_at", "-created_at", "id")
        .values_list("error_message", flat=True)
        .first()
        or ""
    )
    active_requests = sum(
        request_counts[state]
        for state in (
            BookCreationRequestState.INITIAL,
            BookCreationRequestState.QUEUED,
            BookCreationRequestState.PROCESSING,
        )
    )
    on_hold_requests = sum(
        request_counts[state]
        for state in (
            BookCreationRequestState.PAUSED,
            BookCreationRequestState.FAILED,
            BookCreationRequestState.DUPLICATE,
            BookCreationRequestState.DELETED,
        )
    )
    incomplete_counts = processing_incomplete_counts()

    return {
        "catalog": {
            "records": BookRecord.objects.count(),
            "notCreated": BookRecord.objects.filter(
                book_creation_state=BookCreationState.NOT_CREATED
            ).count(),
            "active": active_requests,
            "created": request_counts[BookCreationRequestState.CREATED],
            "onHold": on_hold_requests,
        },
        "create": {
            "requests": request_counts[BookCreationRequestState.INITIAL],
            "queue": request_counts[BookCreationRequestState.QUEUED],
            "processing": request_counts[BookCreationRequestState.PROCESSING],
            "created": request_counts[BookCreationRequestState.CREATED],
        },
        "onHold": {
            "paused": request_counts[BookCreationRequestState.PAUSED],
            "failed": request_counts[BookCreationRequestState.FAILED],
            "duplicate": request_counts[BookCreationRequestState.DUPLICATE],
            "deleted": request_counts[BookCreationRequestState.DELETED],
        },
        "incomplete": incomplete_counts,
        "notifications": {
            "activeRequests": active_requests,
            "createdCount": request_counts[BookCreationRequestState.CREATED],
            "failedCount": request_counts[BookCreationRequestState.FAILED],
            "duplicateCount": request_counts[BookCreationRequestState.DUPLICATE],
            "latestFailedMessage": latest_failed_message,
        },
    }


def processing_card_payload(card):
    if card not in PROCESSING_SHARED_CARD_KEYS:
        raise KeyError(card)
    payload = processing_ui_shared_projection_payload(card)
    return {
        **payload,
        "version": processing_ui_versions_map(domains=[card]).get(card, 0),
    }
