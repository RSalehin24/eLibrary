import re

from django.db.models import Exists, OuterRef, Q, Subquery
from django.utils.dateparse import parse_date, parse_datetime
from rest_framework.response import Response

from apps.catalog.models import Book, BookRecordType, ContributorRole, UserBook
from apps.common.text import normalize_catalog_text
from apps.ingestion.models import BookSubmission


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


def bounded_positive_int(raw_value, *, default, minimum=1, maximum=100):
    try:
        value = int(str(raw_value).strip() or default)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(value, maximum))


def contributor_roles_for_filter(role):
    if role == ContributorRole.EDITOR:
        return (ContributorRole.EDITOR, ContributorRole.COMPILER)
    return (role,) if role in VALID_CONTRIBUTOR_ROLES else ()


class OptionalPaginationListMixin:
    pagination_default_limit = 60
    pagination_max_limit = 100

    def list(self, request, *args, **kwargs):
        if "page" not in request.query_params and "limit" not in request.query_params:
            return super().list(request, *args, **kwargs)

        queryset = self.filter_queryset(self.get_queryset())
        limit_value = bounded_positive_int(
            request.query_params.get("limit"),
            default=self.pagination_default_limit,
            maximum=self.pagination_max_limit,
        )
        page_value = bounded_positive_int(
            request.query_params.get("page"),
            default=1,
            maximum=10_000,
        )
        total_count = queryset.count()
        page_count = max(1, ((total_count - 1) // limit_value) + 1) if total_count else 1
        page_value = min(page_value, page_count)
        start = (page_value - 1) * limit_value
        page_entries = queryset[start : start + limit_value]
        serializer = self.get_serializer(page_entries, many=True)
        return Response(
            {
                "entries": serializer.data,
                "pagination": {
                    "page": page_value,
                    "limit": limit_value,
                    "total_count": total_count,
                    "page_count": page_count,
                    "has_previous": page_value > 1,
                    "has_next": page_value < page_count,
                },
            }
        )


def filtered_book_queryset(queryset, request, *, default_record_type):
    record_type = requested_record_type(request, default_record_type)
    if record_type != "all":
        queryset = queryset.filter(record_type=record_type)
    ownership = request.query_params.get("ownership", "").strip()
    if ownership == "mine":
        queryset = queryset.filter(my_books_added_at__isnull=False)

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
    for param, filters in {
        "writer_code": {"book_contributors__role": ContributorRole.AUTHOR, "book_contributors__contributor__catalog_code": None},
        "writer_slug": {"book_contributors__role": ContributorRole.AUTHOR, "book_contributors__contributor__slug": None},
        "contributor": {},
    }.items():
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
                resolved = {key: (value if current is None else current) for key, current in filters.items()}
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
    sort_map = {"catalog_code": "catalog_code", "-catalog_code": "-catalog_code", "title": "title", "-title": "-title", "created_at": "created_at", "-created_at": "-created_at"}
    if ownership == "mine":
        sort_map.update({"requested_at": "my_books_added_at", "-requested_at": "-my_books_added_at"})
    sort_field = sort_map.get(sort, "-my_books_added_at" if ownership == "mine" else "-created_at")
    return queryset.order_by(sort_field) if sort_field in {"created_at", "-created_at"} else queryset.order_by(sort_field, "-created_at")


class BookQueryMixin:
    default_record_type = BookRecordType.DIGITAL

    def base_queryset(self):
        owned = UserBook.objects.filter(book=OuterRef("pk"), user=self.request.user).order_by("-created_at")
        latest_submission = BookSubmission.objects.filter(linked_book=OuterRef("pk"), submitter=self.request.user).order_by("-created_at").values("created_at")[:1]
        return (
            Book.objects.prefetch_related(
                "book_contributors__contributor",
                "book_series__series",
                "book_categories__category",
                "generated_assets",
                "source_urls",
            )
            .annotate(is_in_my_books=Exists(owned), user_owns_book=Exists(owned), my_books_added_at=Subquery(owned.values("created_at")[:1]), latest_submission_at=Subquery(latest_submission))
            .defer(
                "summary",
                "raw_scraped_metadata",
                "raw_scrape_payload",
                "main_content_html",
                "book_info_html",
                "dedication_html",
                "toc",
                "content_items",
            )
            .filter(deleted_at__isnull=True)
        )

    def get_queryset(self):
        return filtered_book_queryset(self.base_queryset(), self.request, default_record_type=self.default_record_type)
