from rest_framework import serializers

from apps.catalog.models import Book, GeneratedAsset
from apps.common.api_serializers import AdminPaginationSerializer
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
    JobAttempt,
)
from apps.processing.jobs.queries import available_job_actions


class BackgroundBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("id", "title", "slug")
        read_only_fields = fields


class BackgroundSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceCatalogEntry
        fields = ("id", "title")
        read_only_fields = fields


class BackgroundJobSerializer(serializers.ModelSerializer):
    can_edit_book = serializers.BooleanField(read_only=True)
    book = BackgroundBookSerializer(read_only=True, allow_null=True)
    source_record = BackgroundSourceSerializer(read_only=True, allow_null=True)
    pages_fetched = serializers.IntegerField(
        source="checkpoint.pages_fetched", read_only=True, default=0
    )
    discovered_pages = serializers.IntegerField(
        source="checkpoint.discovered_pages", read_only=True, default=0
    )
    discovered_entries = serializers.IntegerField(
        source="checkpoint.discovered_entries", read_only=True, default=0
    )
    more_pages_available = serializers.BooleanField(
        source="checkpoint.more_pages_available", read_only=True, default=False
    )

    stage = serializers.CharField(
        source="latest_stage", read_only=True, allow_null=True
    )
    heartbeat_at = serializers.DateTimeField(
        source="latest_heartbeat_at", read_only=True, allow_null=True
    )
    checkpoint_saved = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()

    def get_checkpoint_saved(self, job) -> bool:
        return bool(job.checkpoint)

    def get_actions(self, job) -> list[str]:
        return available_job_actions(job)

    class Meta:
        model = BackgroundJob
        fields: tuple[str, ...] = (
            "id",
            "kind",
            "state",
            "requested_action",
            "book",
            "source_record",
            "pages_fetched",
            "discovered_pages",
            "discovered_entries",
            "more_pages_available",
            "can_edit_book",
            "asset_id",
            "stage",
            "heartbeat_at",
            "attempt_count",
            "max_attempts",
            "checkpoint_saved",
            "error_code",
            "available_at",
            "created_at",
            "updated_at",
            "finished_at",
            "actions",
        )
        read_only_fields = fields


class JobAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobAttempt
        fields = (
            "id",
            "number",
            "stage",
            "heartbeat_at",
            "created_at",
            "finished_at",
            "error_code",
        )
        read_only_fields = fields


class BackgroundJobDetailSerializer(BackgroundJobSerializer):
    attempts = JobAttemptSerializer(source="recent_attempts", many=True, read_only=True)

    class Meta(BackgroundJobSerializer.Meta):
        fields: tuple[str, ...] = (*BackgroundJobSerializer.Meta.fields, "attempts")


class BackgroundJobCollectionSerializer(serializers.Serializer):
    entries = BackgroundJobSerializer(many=True)
    pagination = AdminPaginationSerializer()


class JobParametersSerializer(serializers.Serializer):
    page = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)
    state = serializers.ChoiceField(choices=BackgroundJobState.choices, required=False)
    kind = serializers.ChoiceField(choices=BackgroundJobKind.choices, required=False)
    book = serializers.UUIDField(required=False)
    automation_run = serializers.UUIDField(required=False)


class JobControlSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    action = serializers.ChoiceField(choices=["pause", "cancel", "resume"])


class PreparationCommandSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    expected_updated_at = serializers.DateTimeField()


class OperationAcceptedSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    status_url = serializers.CharField()


class ProcessingAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedAsset
        fields = ("id", "asset_type", "status", "file_size", "checksum", "updated_at")
        read_only_fields = fields
