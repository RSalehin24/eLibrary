import re

from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import BookRecordType, Category, Contributor, ContributorRole, Series
from apps.catalog.serializers import CategoryListSerializer, ContributorListSerializer, SeriesListSerializer
from apps.common.text import normalize_catalog_text
from apps.ingestion.services.normalization_support.metadata import (
    ENGLISH_PROSE_FRAGMENT_WORDS,
)

from .shared import (
    CONTRIBUTOR_ROLES_BY_PAGE,
    OptionalPaginationListMixin,
    apply_created_at_filters,
    normalized_text_search_clause,
    requested_record_type,
)

PROSE_FRAGMENT_PATTERN = r"(^| )({})($| )".format(
    "|".join(re.escape(word) for word in sorted(ENGLISH_PROSE_FRAGMENT_WORDS))
)


def annotate_reference_counts(queryset, relation, *, record_type, contributor_roles=None, author=None, series=None, category=None):
    base_filter = {f"{relation}__deleted_at__isnull": True}
    if contributor_roles:
        if len(contributor_roles) == 1:
            base_filter["book_contributions__role"] = contributor_roles[0]
        else:
            base_filter["book_contributions__role__in"] = contributor_roles

    if author:
        base_filter[f"{relation}__book_contributors__contributor__name"] = author
        base_filter[f"{relation}__book_contributors__role"] = ContributorRole.AUTHOR
    if series:
        base_filter[f"{relation}__book_series__series__name"] = series
    if category:
        base_filter[f"{relation}__book_categories__category__name"] = category

    def count_filter(target_record_type=None):
        filters = dict(base_filter)
        if target_record_type:
            filters[f"{relation}__record_type"] = target_record_type
        return Q(**filters)

    queryset = queryset.annotate(
        digital_book_count=Count(relation, filter=count_filter(BookRecordType.DIGITAL), distinct=True),
        manual_book_count=Count(relation, filter=count_filter(BookRecordType.MANUAL), distinct=True),
    )
    if record_type == "manual":
        return queryset.annotate(book_count=Count(relation, filter=count_filter(BookRecordType.MANUAL), distinct=True))
    if record_type == "all":
        return queryset.annotate(book_count=Count(relation, filter=count_filter(), distinct=True))
    return queryset.annotate(book_count=Count(relation, filter=count_filter(BookRecordType.DIGITAL), distinct=True))


class CategoryListView(OptionalPaginationListMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = CategoryListSerializer
    pagination_default_limit = 60
    pagination_max_limit = 100

    def get_queryset(self):
        author = self.request.query_params.get("author", "").strip() or self.request.query_params.get("writer", "").strip()
        series = self.request.query_params.get("series", "").strip()
        queryset = annotate_reference_counts(
            Category.objects.all(),
            "books",
            record_type=requested_record_type(self.request, BookRecordType.DIGITAL),
            author=author,
            series=series,
        )
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                normalized_text_search_clause(
                    query,
                    normalize_catalog_text(query),
                    raw_lookup="name",
                    normalized_lookup="normalized_name",
                )
                | Q(catalog_code__icontains=query)
            )
        queryset = apply_created_at_filters(queryset, self.request).filter(book_count__gt=0)
        sort_field = {"catalog_code": "catalog_code", "-catalog_code": "-catalog_code", "name": "name", "-name": "-name", "created_at": "created_at", "-created_at": "-created_at", "book_count": "book_count", "-book_count": "-book_count"}.get(self.request.query_params.get("sort", "-book_count"), "-book_count")
        return queryset.order_by(sort_field) if sort_field in {"created_at", "-created_at"} else queryset.order_by(sort_field, "name")


class SeriesListView(OptionalPaginationListMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = SeriesListSerializer
    pagination_default_limit = 60
    pagination_max_limit = 100

    def get_queryset(self):
        author = self.request.query_params.get("author", "").strip() or self.request.query_params.get("writer", "").strip()
        category = self.request.query_params.get("category", "").strip()
        queryset = annotate_reference_counts(
            Series.objects.all(),
            "books",
            record_type=requested_record_type(self.request, BookRecordType.DIGITAL),
            author=author,
            category=category,
        )
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                normalized_text_search_clause(
                    query,
                    normalize_catalog_text(query),
                    raw_lookup="name",
                    normalized_lookup="normalized_name",
                )
                | Q(catalog_code__icontains=query)
            )
        queryset = apply_created_at_filters(queryset, self.request).filter(book_count__gt=0)
        sort_field = {"catalog_code": "catalog_code", "-catalog_code": "-catalog_code", "name": "name", "-name": "-name", "created_at": "created_at", "-created_at": "-created_at", "book_count": "book_count", "-book_count": "-book_count"}.get(self.request.query_params.get("sort", "-book_count"), "-book_count")
        return queryset.order_by(sort_field) if sort_field in {"created_at", "-created_at"} else queryset.order_by(sort_field, "name")


class ContributorListView(OptionalPaginationListMixin, generics.ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ContributorListSerializer
    role_slug = "writers"
    pagination_default_limit = 60
    pagination_max_limit = 100

    def get_contributor_roles(self):
        role_slug = self.kwargs.get("role") or getattr(self, "role_slug", "writers")
        return CONTRIBUTOR_ROLES_BY_PAGE.get(role_slug, (ContributorRole.AUTHOR,))

    def get_queryset(self):
        roles = self.get_contributor_roles()
        contributors = Contributor.objects.filter(book_contributions__role__in=roles)
        if ContributorRole.PUBLISHER not in roles:
            contributors = contributors.exclude(normalized_name__iregex=PROSE_FRAGMENT_PATTERN)
        series = self.request.query_params.get("series", "").strip()
        category = self.request.query_params.get("category", "").strip()
        queryset = annotate_reference_counts(
            contributors.distinct(),
            "book_contributions__book",
            record_type=requested_record_type(self.request, BookRecordType.DIGITAL),
            contributor_roles=roles,
            series=series,
            category=category,
        )
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = queryset.filter(
                normalized_text_search_clause(
                    query,
                    normalize_catalog_text(query),
                    raw_lookup="name",
                    normalized_lookup="normalized_name",
                )
                | Q(catalog_code__icontains=query)
            )
        queryset = apply_created_at_filters(queryset, self.request).filter(book_count__gt=0)
        sort_field = {"catalog_code": "catalog_code", "-catalog_code": "-catalog_code", "name": "name", "-name": "-name", "created_at": "created_at", "-created_at": "-created_at", "book_count": "book_count", "-book_count": "-book_count"}.get(self.request.query_params.get("sort", "-book_count"), "-book_count")
        return queryset.order_by(sort_field) if sort_field in {"created_at", "-created_at"} else queryset.order_by(sort_field, "name")
