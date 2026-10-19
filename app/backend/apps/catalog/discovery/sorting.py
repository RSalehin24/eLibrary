from typing import ClassVar

from django.core import signing
from django.db.models import CharField, F, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce
from rest_framework import serializers

from apps.catalog.models import UserBook
from apps.common.ranked_pagination import CURSOR_MAX_AGE_SECONDS, CURSOR_SALT

CATALOG_SORTS = (
    "",
    "-created_at",
    "created_at",
    "title",
    "-title",
    "catalog_code",
    "-catalog_code",
    "requested_at",
    "-requested_at",
    "manual_publisher",
    "-manual_publisher",
)
TEXT_SORT_FIELDS = {
    "title": "normalized_title",
    "catalog_code": "catalog_code",
    "manual_publisher": "manual_publisher",
}


class SortCursorSerializer(serializers.Serializer):
    value = serializers.CharField(
        max_length=2048, allow_blank=True, trim_whitespace=False
    )
    id = serializers.UUIDField()
    search_context = serializers.CharField(max_length=64)


def with_requested_at(queryset, actor):
    if actor is None or not actor.is_authenticated:
        return queryset.annotate(requested_at=F("created_at"))
    added = UserBook.objects.filter(book_id=OuterRef("pk"), user=actor).values(
        "created_at"
    )[:1]
    return queryset.annotate(requested_at=Coalesce(Subquery(added), F("created_at")))


def filter_owned_books(queryset, parameters, actor):
    if parameters.get("ownership") != "mine":
        return queryset
    if actor is None or not actor.is_authenticated:
        return queryset.none()
    return queryset.filter(user_books__user=actor)


class CatalogSortPagination:
    ordering_choices: ClassVar[tuple[str, ...]] = CATALOG_SORTS
    text_fields: ClassVar[dict[str, str]] = TEXT_SORT_FIELDS
    number_fields: ClassVar[tuple[str, ...]] = ()

    def __init__(self, ordering):
        self.descending = ordering.startswith("-")
        self.field = ordering.lstrip("-")
        if ordering not in self.ordering_choices or not self.field:
            raise ValueError("Choose a supported catalog ordering.")

    def prepared_queryset(self, queryset):
        field = self.text_fields.get(self.field, self.field)
        value = (
            Coalesce(field, Value(""), output_field=CharField())
            if self.field in self.text_fields
            else F(field)
        )
        return queryset.annotate(catalog_sort_value=value)

    def decode(self, token, context):
        try:
            payload = signing.loads(
                token, salt=CURSOR_SALT + ":sort", max_age=CURSOR_MAX_AGE_SECONDS
            )
        except signing.BadSignature as error:
            raise serializers.ValidationError(
                {"cursor": "This cursor is invalid or expired."}
            ) from error
        serializer = SortCursorSerializer(data=payload)
        if (
            not serializer.is_valid()
            or serializer.validated_data["search_context"] != context
        ):
            raise serializers.ValidationError(
                {"cursor": "This cursor does not match the requested search."}
            )
        position = serializer.validated_data
        if self.field in self.number_fields:
            position["value"] = serializers.IntegerField(min_value=0).run_validation(
                position["value"]
            )
        elif self.field not in self.text_fields:
            position["value"] = serializers.DateTimeField().run_validation(
                position["value"]
            )
        return position

    def encode(self, record, context):
        value = record.catalog_sort_value
        return signing.dumps(
            {
                "value": value.isoformat() if hasattr(value, "isoformat") else value,
                "id": str(record.pk),
                "search_context": context,
            },
            salt=CURSOR_SALT + ":sort",
            compress=True,
        )

    def page(self, queryset, parameters, context):
        queryset = self.prepared_queryset(queryset)
        if parameters.get("cursor"):
            position = self.decode(parameters["cursor"], context)
            comparison = "lt" if self.descending else "gt"
            queryset = queryset.filter(
                Q(**{f"catalog_sort_value__{comparison}": position["value"]})
                | Q(
                    catalog_sort_value=position["value"],
                    **{f"id__{comparison}": position["id"]},
                )
            )
        prefix = "-" if self.descending else ""
        offset, limit = (
            (parameters.get("page", 1) - 1) * parameters["limit"],
            parameters["limit"],
        )
        records = list(
            queryset.order_by(prefix + "catalog_sort_value", prefix + "id")[
                offset : offset + limit + 1
            ]
        )
        entries = records[:limit]
        return entries, self.encode(entries[-1], context) if len(
            records
        ) > limit else None
