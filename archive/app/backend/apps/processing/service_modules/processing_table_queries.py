

def processing_row_search_text(row):
    details = ""
    if row.get("progressCheckpoint"):
        details = row["progressCheckpoint"]
    elif row.get("errorMessage"):
        details = row["errorMessage"]
    elif row.get("duplicateConfirmed"):
        details = "Confirmed duplicate"
    elif row.get("isConfirmedNotDuplicate"):
        details = "Confirmed new"
    elif row.get("isResumed"):
        details = "Resumed from saved progress"

    values = [
        row.get("title"),
        row.get("url"),
        row.get("displayUrl"),
        row.get("displayPath"),
        row.get("writer"),
        row.get("translator"),
        row.get("publisher"),
        row.get("category"),
        processing_state_label(row.get("status")),
        details,
    ]
    return " ".join(str(value or "") for value in values).casefold()


def processing_row_record_query(query):
    if not query:
        return Q()

    return (
        Q(name__icontains=query)
        | Q(url__icontains=query)
        | Q(category__icontains=query)
        | Q(writer__icontains=query)
        | Q(translator__icontains=query)
        | Q(publisher__icontains=query)
        | Q(processing_status__icontains=query)
    )


def processing_row_request_query(query):
    if not query:
        return Q()

    return (
        Q(book_record__name__icontains=query)
        | Q(book_record__url__icontains=query)
        | Q(book_record__category__icontains=query)
        | Q(book_record__writer__icontains=query)
        | Q(book_record__translator__icontains=query)
        | Q(book_record__publisher__icontains=query)
        | Q(state__icontains=query)
        | Q(error_message__icontains=query)
    )


def distinct_nonempty_values(queryset, field_name):
    return sorted(
        {
            value
            for value in queryset.order_by().values_list(field_name, flat=True).distinct()
            if value
        }
    )


def annotate_record_processing_status(queryset):
    latest_request_state = Subquery(
        BookCreationRequest.objects.filter(book_record_id=OuterRef("pk"))
        .order_by("-updated_at", "-created_at", "id")
        .values("state")[:1],
        output_field=CharField(),
    )
    return queryset.annotate(
        latest_request_state=latest_request_state,
    ).annotate(
        processing_status=Coalesce(F("latest_request_state"), F("book_creation_state")),
    )


def order_catalog_records_queryset(queryset):
    return queryset.annotate(
        processing_status_rank=Case(
            When(
                processing_status=BookCreationState.NOT_CREATED,
                then=Value(0),
            ),
            default=Value(1),
            output_field=IntegerField(),
        )
    ).order_by("processing_status_rank", "-updated_at")


def processing_pagination_payload(total_count, offset, limit, returned_count):
    next_offset = offset + returned_count
    return {
        "offset": offset,
        "limit": limit,
        "totalCount": total_count,
        "returnedCount": returned_count,
        "hasMore": next_offset < total_count,
        "nextOffset": next_offset,
    }


def build_processing_record_table_payload(
    queryset,
    *,
    query="",
    category="",
    status="",
    offset=0,
    limit=PROCESSING_TABLE_DEFAULT_LIMIT,
    selectable=True,
    include_facets=True,
):
    category_options = (
        distinct_nonempty_values(queryset, "category") if include_facets else None
    )
    status_options = (
        distinct_nonempty_values(queryset, "processing_status") if include_facets else None
    )

    filtered_queryset = queryset
    if query:
        filtered_queryset = filtered_queryset.filter(processing_row_record_query(query))
    if category:
        filtered_queryset = filtered_queryset.filter(category=category)
    if status:
        filtered_queryset = filtered_queryset.filter(processing_status=status)

    total_count = filtered_queryset.count()
    page_records = list(filtered_queryset[offset : offset + limit])
    rows = []
    for record in page_records:
        latest_request = latest_request_for_record(record)
        rows.append(
            processing_row_payload(
                record,
                latest_request,
                selectable=record_is_selectable(record) if selectable else False,
            )
        )

    pagination = processing_pagination_payload(
        total_count,
        offset,
        limit,
        len(rows),
    )
    return {
        "rows": rows,
        "pagination": pagination,
        "hasMore": pagination["hasMore"],
        **(
            {
                "filters": {
                    "categoryOptions": category_options,
                    "statusOptions": status_options,
                }
            }
            if include_facets
            else {}
        ),
    }


def build_processing_request_table_payload(
    queryset,
    *,
    query="",
    category="",
    status="",
    offset=0,
    limit=PROCESSING_TABLE_DEFAULT_LIMIT,
    include_facets=True,
):
    category_options = (
        distinct_nonempty_values(queryset, "book_record__category")
        if include_facets
        else None
    )
    status_options = (
        distinct_nonempty_values(queryset, "state") if include_facets else None
    )

    filtered_queryset = queryset
    if query:
        filtered_queryset = filtered_queryset.filter(processing_row_request_query(query))
    if category:
        filtered_queryset = filtered_queryset.filter(book_record__category=category)
    if status:
        filtered_queryset = filtered_queryset.filter(state=status)

    total_count = filtered_queryset.count()
    page_requests = list(filtered_queryset[offset : offset + limit])
    rows = [
        processing_row_payload(processing_request.book_record, processing_request)
        for processing_request in page_requests
    ]

    pagination = processing_pagination_payload(
        total_count,
        offset,
        limit,
        len(rows),
    )
    return {
        "rows": rows,
        "pagination": pagination,
        "hasMore": pagination["hasMore"],
        **(
            {
                "filters": {
                    "categoryOptions": category_options,
                    "statusOptions": status_options,
                }
            }
            if include_facets
            else {}
        ),
    }


def catalog_processing_rows():
    rows = []
    queryset = (
        BookRecord.objects.select_related("linked_book")
        .prefetch_related(processing_request_prefetch())
        .order_by("name", "id")
    )
    for record in queryset:
        latest_request = latest_request_for_record(record)
        rows.append(
            processing_row_payload(
                record,
                latest_request,
                selectable=record_is_selectable(record),
            )
        )

    return sorted(
        rows,
        key=lambda row: (
            0 if row["status"] == BookCreationState.NOT_CREATED else 1,
            normalize_category_key(row["title"]),
            row["id"],
        ),
    )
