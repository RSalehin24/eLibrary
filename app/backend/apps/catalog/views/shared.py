import re

from django.db.models import Q
from django.utils.dateparse import parse_date, parse_datetime

from apps.catalog.models import (
    BookRecordType,
    ContributorRole,
)
from apps.common.text import normalize_catalog_text

from .book_queries import BookQueryMixin as BookQueryMixin
from .legacy_pagination import (
    OptionalPaginationListMixin as OptionalPaginationListMixin,
)
from .legacy_pagination import (
    bounded_positive_int as bounded_positive_int,
)

VALID_RECORD_TYPES = {choice for choice, _ in BookRecordType.choices}
VALID_CONTRIBUTOR_ROLES = {choice for choice, _ in ContributorRole.choices}
CONTRIBUTOR_ROLES_BY_PAGE = {
    "writers": (ContributorRole.AUTHOR,),
    "translators": (ContributorRole.TRANSLATOR,),
    "compilers": (ContributorRole.COMPILER,),
    "editors": (ContributorRole.EDITOR, ContributorRole.COMPILER),
    "publishers": (ContributorRole.PUBLISHER,),
}
FLEXIBLE_SEPARATOR_REGEX = r"[\s\-.–—(){}\[\],:;/'\"_|]*"


def separator_flexible_pattern(normalized_query):
    tokens = [re.escape(token) for token in normalized_query.split() if token]
    if len(tokens) < 2:
        return ""
    return FLEXIBLE_SEPARATOR_REGEX.join(tokens)


def normalized_text_search_clause(raw_query, normalized_query, *, raw_lookup, normalized_lookup=""):
    clause = Q(**{f"{raw_lookup}__icontains": raw_query})
    if normalized_lookup and normalized_query:
        clause |= Q(**{f"{normalized_lookup}__contains": normalized_query})
    flexible_pattern = separator_flexible_pattern(normalized_query)
    if flexible_pattern:
        clause |= Q(**{f"{raw_lookup}__iregex": flexible_pattern})
    return clause


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


def requested_record_type(request, default_record_type):
    record_type = request.query_params.get("record_type", "").strip()
    if record_type == "all":
        return "all"
    if record_type in VALID_RECORD_TYPES:
        return record_type
    return default_record_type


def export_record_type(request, default_record_type):
    record_type = requested_record_type(request, default_record_type)
    return "all" if record_type == "all" else record_type




def contributor_roles_for_filter(role):
    if role == ContributorRole.EDITOR:
        return (ContributorRole.EDITOR, ContributorRole.COMPILER)
    return (role,) if role in VALID_CONTRIBUTOR_ROLES else ()




def filtered_book_queryset(queryset, request, *, default_record_type):
    record_type = requested_record_type(request, default_record_type)
    if record_type != "all":
        queryset = queryset.filter(record_type=record_type)
    ownership = request.query_params.get("ownership", "").strip()
    if ownership == "mine":
        queryset = queryset.filter(my_books_added_at__isnull=False)

    kindle_sent = request.query_params.get("kindle_sent", "").strip()
    if kindle_sent == "mine":
        queryset = queryset.filter(user_kindle_sent_at__isnull=False)

    query = request.query_params.get("q", "").strip()
    if query:
        normalized_query = normalize_catalog_text(query)
        submission_query = Q(linked_submissions__original_input__icontains=query)
        if normalized_query:
            submission_query |= Q(linked_submissions__normalized_input__contains=normalized_query)
        if ownership == "mine":
            submission_query &= Q(linked_submissions__submitter=request.user)
        queryset = queryset.filter(
            Q(catalog_code__icontains=query)
            | normalized_text_search_clause(
                query,
                normalized_query,
                raw_lookup="title",
                normalized_lookup="normalized_title",
            )
            | normalized_text_search_clause(
                query,
                normalized_query,
                raw_lookup="book_contributors__contributor__name",
                normalized_lookup="book_contributors__contributor__normalized_name",
            )
            | Q(book_contributors__contributor__catalog_code__icontains=query)
            | normalized_text_search_clause(
                query,
                normalized_query,
                raw_lookup="book_series__series__name",
                normalized_lookup="book_series__series__normalized_name",
            )
            | normalized_text_search_clause(
                query,
                normalized_query,
                raw_lookup="book_categories__category__name",
                normalized_lookup="book_categories__category__normalized_name",
            )
            | Q(book_categories__category__catalog_code__icontains=query)
            | submission_query
        )

    filter_map = {
        "book_code": {"catalog_code__icontains": None},
        "category_code": {"book_categories__category__catalog_code": None},
        "category_slug": {"book_categories__category__slug": None},
        "state": {"state": None},
        "review_state": {"review_state": None},
        "submission_status": {"linked_submissions__status": None},
        "processing_status": {"processing_jobs__status": None},
    }
    for param, filters in filter_map.items():
        value = request.query_params.get(param, "").strip()
        if value:
            field = next(iter(filters))
            queryset = queryset.filter(**{field: value})

    series = request.query_params.get("series", "").strip()
    if series:
        queryset = queryset.filter(
            normalized_text_search_clause(
                series,
                normalize_catalog_text(series),
                raw_lookup="book_series__series__name",
                normalized_lookup="book_series__series__normalized_name",
            )
        )

    category = request.query_params.get("category", "").strip()
    if category:
        queryset = queryset.filter(
            normalized_text_search_clause(
                category,
                normalize_catalog_text(category),
                raw_lookup="book_categories__category__name",
                normalized_lookup="book_categories__category__normalized_name",
            )
        )

    author = request.query_params.get("author", "").strip() or request.query_params.get("writer", "").strip()
    if author:
        queryset = queryset.filter(book_contributors__role=ContributorRole.AUTHOR).filter(
            normalized_text_search_clause(
                author,
                normalize_catalog_text(author),
                raw_lookup="book_contributors__contributor__name",
                normalized_lookup="book_contributors__contributor__normalized_name",
            )
        )

    translator = request.query_params.get("translator", "").strip()
    if translator:
        queryset = queryset.filter(book_contributors__role=ContributorRole.TRANSLATOR).filter(
            normalized_text_search_clause(
                translator,
                normalize_catalog_text(translator),
                raw_lookup="book_contributors__contributor__name",
                normalized_lookup="book_contributors__contributor__normalized_name",
            )
        )

    editor = request.query_params.get("editor", "").strip()
    if editor:
        queryset = queryset.filter(
            book_contributors__role__in=(ContributorRole.EDITOR, ContributorRole.COMPILER)
        ).filter(
            normalized_text_search_clause(
                editor,
                normalize_catalog_text(editor),
                raw_lookup="book_contributors__contributor__name",
                normalized_lookup="book_contributors__contributor__normalized_name",
            )
        )

    publisher = request.query_params.get("publisher", "").strip()
    if publisher:
        queryset = queryset.filter(
            Q(book_contributors__role=ContributorRole.PUBLISHER)
            & normalized_text_search_clause(
                publisher,
                normalize_catalog_text(publisher),
                raw_lookup="book_contributors__contributor__name",
                normalized_lookup="book_contributors__contributor__normalized_name",
            )
        )

    binding = request.query_params.get("binding", "").strip()
    if binding:
        queryset = queryset.filter(manual_binding=binding)

    reference_filters: dict[str, dict[str, ContributorRole | None]] = {
        "writer_code": {"book_contributors__role": ContributorRole.AUTHOR, "book_contributors__contributor__catalog_code": None},
        "writer_slug": {"book_contributors__role": ContributorRole.AUTHOR, "book_contributors__contributor__slug": None},
        "contributor": {},
    }
    for param, contributor_match in reference_filters.items():
        value = request.query_params.get(param, "").strip()
        if value:
            if param == "contributor":
                role_filters = contributor_roles_for_filter(
                    request.query_params.get("contributor_role", "").strip()
                )
                queryset = queryset.filter(
                    Q(book_contributors__role__in=role_filters) if role_filters else Q()
                ).filter(
                    normalized_text_search_clause(
                        value,
                        normalize_catalog_text(value),
                        raw_lookup="book_contributors__contributor__name",
                        normalized_lookup="book_contributors__contributor__normalized_name",
                    )
                )
            else:
                resolved = {key: (value if current is None else current) for key, current in contributor_match.items()}
                queryset = queryset.filter(**resolved)

    contributor_role = request.query_params.get("contributor_role", "").strip()
    for param, field in {
        "contributor_code": "book_contributors__contributor__catalog_code",
        "contributor_slug": "book_contributors__contributor__slug",
    }.items():
        value = request.query_params.get(param, "").strip()
        if value:
            contributor_filters = {field: value}
            role_filters = contributor_roles_for_filter(contributor_role)
            if len(role_filters) == 1:
                contributor_filters["book_contributors__role"] = role_filters[0]
            elif len(role_filters) > 1:
                contributor_filters["book_contributors__role__in"] = role_filters
            queryset = queryset.filter(**contributor_filters)

    queryset = apply_created_at_filters(queryset, request).distinct()
    sort = request.query_params.get("sort", "-requested_at" if ownership == "mine" else "-created_at")
    sort_map = {
        "catalog_code": "catalog_code",
        "-catalog_code": "-catalog_code",
        "title": "title",
        "-title": "-title",
        "created_at": "created_at",
        "-created_at": "-created_at",
        "manual_publisher": "manual_publisher",
        "-manual_publisher": "-manual_publisher",
    }
    if ownership == "mine":
        sort_map.update({"requested_at": "my_books_added_at", "-requested_at": "-my_books_added_at"})
    if kindle_sent == "mine":
        sort_map.update({"sent_at": "user_kindle_sent_at", "-sent_at": "-user_kindle_sent_at"})
    sort_field = sort_map.get(sort, "-my_books_added_at" if ownership == "mine" else "-user_kindle_sent_at" if kindle_sent == "mine" else "-created_at")
    return queryset.order_by(sort_field) if sort_field in {"created_at", "-created_at"} else queryset.order_by(sort_field, "-created_at")
