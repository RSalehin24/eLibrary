import re
from typing import ClassVar

from django.db.models import Count, Q
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from apps.catalog.models import Category, Contributor, ContributorRole, Series
from apps.catalog.serializers import (
    CategoryListSerializer,
    ContributorListSerializer,
    SeriesListSerializer,
)
from apps.common.text import normalize_catalog_text
from apps.ingestion.services.normalization_support.metadata import (
    ENGLISH_PROSE_FRAGMENT_WORDS,
)

from .shared import (
    CONTRIBUTOR_ROLES_BY_PAGE,
    OptionalPaginationListMixin,
    apply_created_at_filters,
    normalized_text_search_clause,
)

PROSE_FRAGMENT_PATTERN = r"(^| )({})($| )".format(
    "|".join(re.escape(word) for word in sorted(ENGLISH_PROSE_FRAGMENT_WORDS))
)


def annotate_reference_counts(queryset, relation, **selection):
    filters = {f"{relation}__deleted_at__isnull": True}
    if roles := selection.get("contributor_roles"):
        filters["book_contributions__role__in"] = roles
    if author := selection.get("author"):
        filters[f"{relation}__book_contributors__contributor__name"] = author
        filters[f"{relation}__book_contributors__role"] = ContributorRole.AUTHOR
    for kind in ("series", "category"):
        if value := selection.get(kind):
            field = (
                "book_series__series__name"
                if kind == "series"
                else "book_categories__category__name"
            )
            filters[f"{relation}__{field}"] = value
    return queryset.annotate(
        book_count=Count(relation, filter=Q(**filters), distinct=True)
    )


class CategoryListView(OptionalPaginationListMixin, generics.ListAPIView):
    permission_classes: ClassVar = [IsAuthenticated]
    serializer_class = CategoryListSerializer
    pagination_default_limit = 60
    pagination_max_limit = 100

    def get_queryset(self):
        author = (
            self.request.query_params.get("author", "").strip()
            or self.request.query_params.get("writer", "").strip()
        )
        series = self.request.query_params.get("series", "").strip()
        queryset = annotate_reference_counts(
            Category.objects.all(),
            "books",
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
        queryset = apply_created_at_filters(queryset, self.request).filter(
            book_count__gt=0
        )
        sort_field = {
            "catalog_code": "catalog_code",
            "-catalog_code": "-catalog_code",
            "name": "name",
            "-name": "-name",
            "created_at": "created_at",
            "-created_at": "-created_at",
            "book_count": "book_count",
            "-book_count": "-book_count",
        }.get(self.request.query_params.get("sort", "-book_count"), "-book_count")
        return (
            queryset.order_by(sort_field)
            if sort_field in {"created_at", "-created_at"}
            else queryset.order_by(sort_field, "name")
        )


class SeriesListView(OptionalPaginationListMixin, generics.ListAPIView):
    permission_classes: ClassVar = [IsAuthenticated]
    serializer_class = SeriesListSerializer
    pagination_default_limit = 60
    pagination_max_limit = 100

    def get_queryset(self):
        author = (
            self.request.query_params.get("author", "").strip()
            or self.request.query_params.get("writer", "").strip()
        )
        category = self.request.query_params.get("category", "").strip()
        queryset = annotate_reference_counts(
            Series.objects.all(),
            "books",
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
        queryset = apply_created_at_filters(queryset, self.request).filter(
            book_count__gt=0
        )
        sort_field = {
            "catalog_code": "catalog_code",
            "-catalog_code": "-catalog_code",
            "name": "name",
            "-name": "-name",
            "created_at": "created_at",
            "-created_at": "-created_at",
            "book_count": "book_count",
            "-book_count": "-book_count",
        }.get(self.request.query_params.get("sort", "-book_count"), "-book_count")
        return (
            queryset.order_by(sort_field)
            if sort_field in {"created_at", "-created_at"}
            else queryset.order_by(sort_field, "name")
        )


class ContributorListView(OptionalPaginationListMixin, generics.ListAPIView):
    permission_classes: ClassVar = [IsAuthenticated]
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
            contributors = contributors.exclude(
                normalized_name__iregex=PROSE_FRAGMENT_PATTERN
            )
        series = self.request.query_params.get("series", "").strip()
        category = self.request.query_params.get("category", "").strip()
        queryset = annotate_reference_counts(
            contributors.distinct(),
            "book_contributions__book",
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
        queryset = apply_created_at_filters(queryset, self.request).filter(
            book_count__gt=0
        )
        sort_field = {
            "catalog_code": "catalog_code",
            "-catalog_code": "-catalog_code",
            "name": "name",
            "-name": "-name",
            "created_at": "created_at",
            "-created_at": "-created_at",
            "book_count": "book_count",
            "-book_count": "-book_count",
        }.get(self.request.query_params.get("sort", "-book_count"), "-book_count")
        return (
            queryset.order_by(sort_field)
            if sort_field in {"created_at", "-created_at"}
            else queryset.order_by(sort_field, "name")
        )
