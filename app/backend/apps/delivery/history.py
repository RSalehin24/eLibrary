import hashlib
import json
from datetime import datetime, time
from typing import ClassVar
from zoneinfo import ZoneInfo

from django.db.models import F, IntegerField, Value
from rest_framework import serializers

from apps.catalog.discovery.queries import filter_public_books, search_public_books
from apps.catalog.discovery.sorting import CatalogSortPagination
from apps.catalog.models import Book
from apps.catalog.serializers.public import (
    CatalogQueryParametersSerializer,
    ReaderPageParametersSerializer,
)
from apps.common.ranked_pagination import ranked_page
from apps.processing.job_models import BackgroundJobState

KINDLE_SORTS = ("-sent_at", "sent_at", "-created_at", "created_at", "title", "-title")
HISTORY_FILTERS = (
    "q",
    "contributor",
    "category",
    "series",
    "record_type",
    "state",
    "from_date",
    "to_date",
    "sort",
)


class KindleHistoryParametersSerializer(
    CatalogQueryParametersSerializer, ReaderPageParametersSerializer
):
    contributor = serializers.CharField(max_length=255, allow_blank=True, default="")
    category = serializers.CharField(max_length=255, allow_blank=True, default="")
    series = serializers.CharField(max_length=255, allow_blank=True, default="")
    record_type = serializers.ChoiceField(
        choices=("all", "digital", "manual"), default="all"
    )
    state = serializers.ChoiceField(
        choices=("", *BackgroundJobState.values), allow_blank=True, default=""
    )
    sort = serializers.ChoiceField(choices=KINDLE_SORTS, default="-sent_at")
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)

    def validate(self, attrs):
        attrs = super().validate(attrs)
        if (
            attrs.get("from_date")
            and attrs.get("to_date")
            and attrs["from_date"] > attrs["to_date"]
        ):
            raise serializers.ValidationError(
                {"to_date": "Choose an end date on or after the start date."}
            )
        return attrs


class KindleSortPagination(CatalogSortPagination):
    ordering_choices: ClassVar[tuple[str, ...]] = KINDLE_SORTS
    text_fields: ClassVar[dict[str, str]] = {"title": "book__normalized_title"}

    def prepared_queryset(self, queryset):
        fields = {
            "sent_at": "created_at",
            "created_at": "book__created_at",
            **self.text_fields,
        }
        return queryset.annotate(catalog_sort_value=F(fields[self.field]))


def filter_history(queryset, parameters):
    filters = {
        "contributor": parameters["contributor"],
        "contributor_role": "author" if parameters["contributor"] else "",
        "category": parameters["category"],
        "series": parameters["series"],
        "record_type": parameters["record_type"],
    }
    books = filter_public_books(Book.objects.all(), filters)
    books = search_public_books(books, parameters["q"])
    queryset = queryset.filter(book_id__in=books.values("pk"))
    if parameters["state"]:
        queryset = queryset.filter(state=parameters["state"])
    if value := parameters.get("from_date"):
        queryset = queryset.filter(
            created_at__gte=datetime.combine(value, time(), ZoneInfo("Asia/Dhaka"))
        )
    if value := parameters.get("to_date"):
        end = datetime.combine(value, time.max, ZoneInfo("Asia/Dhaka"))
        queryset = queryset.filter(created_at__lte=end)
    return queryset


def history_page(queryset, parameters, actor):
    context = f"kindle:{actor.pk}"
    filtered = (
        any(
            parameters.get(key)
            for key in HISTORY_FILTERS
            if key not in ("record_type", "sort")
        )
        or parameters["record_type"] != "all"
    )
    if not filtered and parameters["sort"] == "-sent_at":
        return ranked_page(
            queryset.annotate(search_rank=Value(0, output_field=IntegerField())),
            parameters,
            context,
        )
    values = {key: str(parameters.get(key, "")) for key in HISTORY_FILTERS}
    digest = hashlib.sha256(
        json.dumps([context, values], sort_keys=True).encode()
    ).hexdigest()
    return KindleSortPagination(parameters["sort"]).page(
        filter_history(queryset, parameters), parameters, digest
    )
