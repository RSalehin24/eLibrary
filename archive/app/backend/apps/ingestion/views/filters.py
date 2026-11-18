from urllib.parse import quote

from django.db.models import Case, IntegerField, Q, Value, When
from django.utils.dateparse import parse_date, parse_datetime

from apps.ingestion.models import SubmissionOrigin

CATALOG_ORIGIN_VALUES = (SubmissionOrigin.CURATION, SubmissionOrigin.AUTOMATION)
INCOMPLETE_CATEGORY_KEYWORDS = ("unfinished", "অসম্পূর্ণ বই", "অসম্পূর্ণ")


def apply_submission_origin_filter(queryset, origin, *, field_name="origin"):
    origin = (origin or "").strip()
    if not origin:
        return queryset
    if origin == "catalog":
        return queryset.filter(**{f"{field_name}__in": CATALOG_ORIGIN_VALUES})
    return queryset.filter(**{field_name: origin})


def normalize_status_filter(value):
    return "cancelled" if value == "stopped" else value


def search_query_variants(query):
    compact = " ".join((query or "").split())
    if not compact:
        return []

    variants = [compact]
    slug_variant = "-".join(compact.split())
    if slug_variant != compact:
        variants.append(slug_variant)

    for value in list(variants):
        encoded_value = quote(value, safe="")
        if encoded_value and encoded_value != value:
            variants.append(encoded_value)

    return list(dict.fromkeys(variants))


def apply_text_search(queryset, query, *field_names):
    variants = search_query_variants(query)
    if not variants or not field_names:
        return queryset

    combined_query = None
    for value in variants:
        value_query = None
        for field_name in field_names:
            clause = Q(**{f"{field_name}__icontains": value})
            value_query = clause if value_query is None else value_query | clause
        combined_query = value_query if combined_query is None else combined_query | value_query

    return queryset.filter(combined_query)


def has_incomplete_keyword(value):
    normalized = (value or "").strip().lower()
    if not normalized:
        return False
    return any(keyword in normalized for keyword in INCOMPLETE_CATEGORY_KEYWORDS)


def apply_created_at_filters(queryset, request):
    created_after = request.query_params.get("created_after", "").strip()
    created_before = request.query_params.get("created_before", "").strip()
    if created_after:
        parsed_after = parse_datetime(created_after) or parse_date(created_after)
        if parsed_after:
            queryset = queryset.filter(created_at__gte=parsed_after)
    if created_before:
        parsed_before = parse_datetime(created_before) or parse_date(created_before)
        if parsed_before:
            queryset = queryset.filter(created_at__lte=parsed_before)
    return queryset


def apply_limit(queryset, request, *, default_limit=80, max_limit=200):
    limit = request.query_params.get("limit", "").strip()
    try:
        limit_value = max(1, min(int(limit), max_limit)) if limit else default_limit
    except (TypeError, ValueError):
        limit_value = default_limit
    return queryset[:limit_value] if limit_value else queryset


def status_order_expression(field_name, ordered_values):
    return Case(
        *[When(**{field_name: value}, then=Value(index)) for index, value in enumerate(ordered_values)],
        default=Value(len(ordered_values)),
        output_field=IntegerField(),
    )


def catalog_snapshot_timestamp(snapshot, *field_names):
    for field_name in field_names:
        value = snapshot.get(field_name)
        if value:
            return value.timestamp()
    return 0


def sort_source_catalog_snapshots(snapshots, sort_key):
    status_order = {
        "processing": 0,
        "failed": 1,
        "stopped": 2,
        "unfinished": 3,
        "new": 4,
        "ready": 5,
        "deleted": 6,
    }
    if sort_key == "created_desc":
        snapshots.sort(key=lambda snapshot: (-catalog_snapshot_timestamp(snapshot, "created_at"), snapshot["title"].lower()))
        return
    if sort_key == "created_asc":
        snapshots.sort(key=lambda snapshot: (catalog_snapshot_timestamp(snapshot, "created_at"), snapshot["title"].lower()))
        return
    if sort_key == "activity_desc":
        snapshots.sort(
            key=lambda snapshot: (
                -catalog_snapshot_timestamp(snapshot, "activity_at", "updated_at", "last_seen_at"),
                snapshot["title"].lower(),
            )
        )
        return
    if sort_key == "activity_asc":
        snapshots.sort(
            key=lambda snapshot: (
                catalog_snapshot_timestamp(snapshot, "activity_at", "updated_at", "last_seen_at"),
                snapshot["title"].lower(),
            )
        )
        return
    if sort_key == "title_asc":
        snapshots.sort(key=lambda snapshot: snapshot["title"].lower())
        return
    if sort_key == "title_desc":
        snapshots.sort(key=lambda snapshot: snapshot["title"].lower(), reverse=True)
        return
    snapshots.sort(
        key=lambda snapshot: (
            status_order.get(snapshot["curation_status"], 99),
            -catalog_snapshot_timestamp(snapshot, "activity_at", "updated_at", "last_seen_at"),
            snapshot["title"].lower(),
        )
    )


__all__ = [
    "INCOMPLETE_CATEGORY_KEYWORDS",
    "apply_created_at_filters",
    "apply_limit",
    "apply_submission_origin_filter",
    "apply_text_search",
    "catalog_snapshot_timestamp",
    "has_incomplete_keyword",
    "normalize_status_filter",
    "search_query_variants",
    "sort_source_catalog_snapshots",
    "status_order_expression",
]
