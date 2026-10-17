from urllib.parse import urlsplit, urlunsplit

from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import URLValidator
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.catalog.models import Book
from apps.common.api_serializers import AdminPaginationSerializer
from apps.ingestion.pipeline.scraper_support.network import normalize_source_url
from apps.ingestion.source_processing.policy import require_source_url, source_hosts
from apps.ingestion.source_processing.verification_serializers import (
    SourceVerificationSerializer,
)
from apps.processing.jobs.execution_errors import ExecutionFailure


class SourceParametersSerializer(serializers.Serializer):
    catalog_scope = serializers.ChoiceField(
        choices=("all", "unfinished"), default="all"
    )
    q = serializers.CharField(
        max_length=200, required=False, default="", allow_blank=True
    )
    page = serializers.IntegerField(min_value=1, required=False, default=1)
    limit = serializers.IntegerField(
        min_value=1, max_value=100, required=False, default=50
    )
    status = serializers.ChoiceField(
        choices=("all", "unlinked", "linked", "removed"), default="all"
    )


class SourceBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("id", "title", "slug", "state", "deleted_at")
        read_only_fields = fields


def present_source_url(value):
    try:
        URLValidator(schemes=("http", "https"))(value)
        url = urlsplit(value)
        if (
            url.scheme not in {"http", "https"}
            or not url.hostname
            or url.username
            or url.password
        ):
            return None
        if url.port is not None and not 1 <= url.port <= 65535:
            return None
        if any(character.isspace() or ord(character) < 32 for character in value):
            return None
        return urlunsplit((url.scheme, url.netloc, url.path, "", ""))
    except (ValueError, DjangoValidationError):
        return None


class SourceContentSummarySerializer(serializers.Serializer):
    verification = SourceVerificationSerializer(allow_null=True)
    body_character_count = serializers.IntegerField()
    chapter_count = serializers.IntegerField()
    check_completeness = serializers.BooleanField()


class SourceEntrySerializer(serializers.Serializer):
    content_summary = serializers.SerializerMethodField()
    id = serializers.UUIDField(source="entry.id")
    title = serializers.CharField(source="entry.title")

    author_line = serializers.CharField(source="entry.author_line")
    source_url = serializers.SerializerMethodField()
    created_at = serializers.DateTimeField(source="entry.created_at")
    last_seen_at = serializers.DateTimeField(source="entry.last_seen_at")
    updated_at = serializers.DateTimeField(source="entry.updated_at")
    book = SourceBookSerializer(read_only=True, allow_null=True)
    can_edit_book = serializers.BooleanField()
    active_operation_id = serializers.UUIDField(
        source="entry.active_operation_id",
        default=None,
        allow_null=True,
        read_only=True,
    )
    can_process = serializers.SerializerMethodField()
    latest_operation_id = serializers.UUIDField(
        source="entry.latest_operation_id",
        default=None,
        allow_null=True,
        read_only=True,
    )

    @extend_schema_field(SourceContentSummarySerializer(allow_null=True))
    def get_content_summary(self, snapshot):
        return self.context.get("content_summary")

    def get_can_process(self, snapshot) -> bool:
        if snapshot.book is not None or getattr(
            snapshot.entry, "active_operation_id", None
        ):
            return False
        try:
            url = require_source_url(snapshot.entry.source_url, source_hosts())
            return normalize_source_url(url) == url
        except (ExecutionFailure, ValueError):
            return False

    @extend_schema_field(serializers.URLField(allow_null=True))
    def get_source_url(self, snapshot):
        return present_source_url(snapshot.entry.source_url)


class SourceEntryCollectionSerializer(serializers.Serializer):
    entries = SourceEntrySerializer(many=True)
    pagination = AdminPaginationSerializer()
