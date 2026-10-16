from django.core import signing
from django.db.models import Q
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

CURSOR_SALT = "catalog.discovery.v1"
CURSOR_MAX_AGE_SECONDS = 24 * 60 * 60
RANKED_ORDERING = ("search_rank", "-created_at", "-id")
POSTGRES_INTEGER_MAX = 2**31 - 1


class CursorPositionSerializer(serializers.Serializer):
    search_rank = serializers.IntegerField(min_value=0, max_value=POSTGRES_INTEGER_MAX)
    created_at = serializers.DateTimeField()
    id = serializers.UUIDField()
    search_context = serializers.CharField()


def decode_cursor(token, context):
    try:
        payload = signing.loads(token, salt=CURSOR_SALT, max_age=CURSOR_MAX_AGE_SECONDS)
    except signing.BadSignature as exc:
        raise ValidationError(
            {"cursor": ["This cursor is invalid or expired."]}
        ) from exc
    position = CursorPositionSerializer(data=payload)
    if not position.is_valid() or position.validated_data["search_context"] != context:
        raise ValidationError(
            {"cursor": ["This cursor does not match the requested search."]}
        )
    return position.validated_data


def encode_cursor(record, context):
    return RankedFeedPagination("created_at").encode(record, context)


def after_position(queryset, position):
    return RankedFeedPagination("created_at").after(queryset, position)


def ranked_page(queryset, parameters, context):
    return RankedFeedPagination("created_at").page(queryset, parameters, context)


class RankedFeedPagination:
    def __init__(self, timestamp_field):
        self.timestamp_field = timestamp_field

    def encode(self, record, context):
        return signing.dumps(
            {
                "search_rank": record.search_rank,
                "created_at": getattr(record, self.timestamp_field).isoformat(),
                "id": str(record.pk),
                "search_context": context,
            },
            salt=CURSOR_SALT,
            compress=True,
        )

    def after(self, queryset, position):
        rank, timestamp = position["search_rank"], position["created_at"]
        return queryset.filter(
            Q(search_rank__gt=rank)
            | Q(search_rank=rank, **{f"{self.timestamp_field}__lt": timestamp})
            | Q(
                search_rank=rank,
                id__lt=position["id"],
                **{self.timestamp_field: timestamp},
            )
        )

    def page(self, queryset, parameters, context):
        if parameters["cursor"]:
            queryset = self.after(
                queryset, decode_cursor(parameters["cursor"], context)
            )
        limit = parameters["limit"]
        offset = (parameters.get("page", 1) - 1) * limit
        ordering = ("search_rank", f"-{self.timestamp_field}", "-id")
        records = list(queryset.order_by(*ordering)[offset : offset + limit + 1])
        entries = records[:limit]
        return entries, self.encode(entries[-1], context) if len(
            records
        ) > limit else None
