from datetime import datetime, time
from zoneinfo import ZoneInfo

from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework.exceptions import ValidationError

from apps.catalog.discovery.entities import public_entities
from apps.catalog.discovery.publication import public_books
from apps.common.text import normalize_catalog_text

from .directory_counts import with_directory_counts


def directory_queryset(kind, parameters):
    if (
        kind == "collections"
        and parameters.get("sort", "").lstrip("-") == "catalog_code"
    ):
        raise ValidationError({"sort": "Collections do not have catalog codes."})
    fields: tuple[str, ...] = ("id", "name", "slug", "created_at")
    if kind != "collections":
        fields += ("catalog_code",)
    queryset = with_directory_counts(
        public_entities(kind).only(*fields), kind, parameters
    )
    queryset = filter_directory_dates(queryset, parameters)
    if role := parameters.get("role"):
        if kind != "contributors":
            raise ValidationError({"role": "Roles apply to contributors."})
        queryset = queryset.filter(
            book_contributions__role=role,
            book_contributions__book_id__in=public_books().values("pk"),
        ).distinct()
    normalized = normalize_catalog_text(parameters["q"])
    if not normalized:
        return queryset.annotate(search_rank=Value(0, output_field=IntegerField()))
    matching = Q(normalized_name__contains=normalized) | Q(
        normalized_aliases__contains=normalized
    )
    exact = Q(normalized_name=normalized)
    if kind != "collections":
        code = Q(catalog_code__iexact=parameters["q"].strip())
        matching |= code
        exact |= code
    return queryset.filter(matching).annotate(
        search_rank=Case(
            When(exact, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    )


def filter_directory_dates(queryset, parameters):
    if value := parameters.get("created_after"):
        queryset = queryset.filter(
            created_at__gte=datetime.combine(value, time(), ZoneInfo("Asia/Dhaka"))
        )
    if value := parameters.get("created_before"):
        queryset = queryset.filter(
            created_at__lte=datetime.combine(value, time.max, ZoneInfo("Asia/Dhaka"))
        )
    return queryset
