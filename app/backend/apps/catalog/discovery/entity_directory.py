from django.db.models import Case, IntegerField, Q, Value, When
from rest_framework.exceptions import ValidationError

from apps.catalog.discovery.entities import public_entities
from apps.catalog.discovery.publication import public_books
from apps.common.text import normalize_catalog_text


def directory_queryset(kind, parameters):
    queryset = public_entities(kind).only("id", "name", "slug", "created_at")
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
    return queryset.filter(
        Q(normalized_name__contains=normalized)
        | Q(normalized_aliases__contains=normalized)
    ).annotate(
        search_rank=Case(
            When(normalized_name=normalized, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        )
    )
