from django.utils import timezone
from rest_framework import serializers

from apps.catalog.models import Book, GeneratedAsset
from apps.common.api_serializers import AdminPaginationSerializer
from apps.ingestion.models import SourceCatalogEntry
from apps.ingestion.source_processing.layout import SourceLayoutSerializer
from apps.ingestion.source_processing.verification_serializers import (
    SourceVerificationSerializer,
)
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
    JobAttempt,
)
from apps.processing.jobs.queries import available_job_actions
from apps.processing.jobs.source_bulk_controls import available_source_bulk_actions
from apps.processing.jobs.source_defects import SourceDefectSerializer

JOB_CONTROL_ACTIONS = ("pause", "cancel", "resume")


class BackgroundBookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ("id", "title", "slug", "updated_at")
        read_only_fields = fields


class BackgroundSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SourceCatalogEntry
        fields = ("id", "title")
        read_only_fields = fields


class BackgroundJobSerializer(serializers.ModelSerializer):
    source_defect = SourceDefectSerializer(
        source="checkpoint.source_defect",
        read_only=True,
        allow_null=True,
        default=None,
    )
    source_layout = SourceLayoutSerializer(
        source="checkpoint.source_summary.layout",
        read_only=True,
        allow_null=True,
        default=None,
    )
    verification = SourceVerificationSerializer(
        source="checkpoint.source_summary.verification",
        read_only=True,
        allow_null=True,
        default=None,
    )
    exports_verified = serializers.BooleanField(
        source="checkpoint.exports_verified", read_only=True, default=False
    )
    bulk_total = serializers.IntegerField(
        source="checkpoint.bulk_total", read_only=True, default=0
    )
    bulk_queued = serializers.IntegerField(
        source="checkpoint.bulk_queued", read_only=True, default=0
    )
    bulk_rejected = serializers.IntegerField(
        source="checkpoint.bulk_rejected", read_only=True, default=0
    )
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
    source_recovery_actions = serializers.SerializerMethodField()

    def get_checkpoint_saved(self, job) -> bool:
        return bool(job.checkpoint)

    def get_actions(self, job) -> list[str]:
        return available_job_actions(job)

    def get_source_recovery_actions(self, job) -> list[str]:
        return available_source_bulk_actions(job)

    class Meta:
        model = BackgroundJob
        fields: tuple[str, ...] = (
            "id",
            "kind",
            "bulk_total",
            "bulk_queued",
            "bulk_rejected",
            "parent_job_id",
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
            "verification",
            "source_layout",
            "source_defect",
            "exports_verified",
            "available_at",
            "created_at",
            "updated_at",
            "finished_at",
            "actions",
            "source_recovery_actions",
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
    queue_ahead = serializers.SerializerMethodField()

    def get_queue_ahead(self, job) -> int | None:
        if (
            job.kind != BackgroundJobKind.PROCESS_SOURCE
            or job.state
            not in {BackgroundJobState.QUEUED, BackgroundJobState.RETRY_WAIT}
            or job.available_at > timezone.now()
        ):
            return None
        return BackgroundJob.objects.filter(
            kind=job.kind,
            state=BackgroundJobState.QUEUED,
            available_at__lte=timezone.now(),
            created_at__lt=job.created_at,
        ).count()

    class Meta(BackgroundJobSerializer.Meta):
        fields: tuple[str, ...] = (
            *BackgroundJobSerializer.Meta.fields,
            "attempts",
            "queue_ahead",
        )


class BackgroundJobCollectionSerializer(serializers.Serializer):
    entries = BackgroundJobSerializer(many=True)
    pagination = AdminPaginationSerializer()


class JobParametersSerializer(serializers.Serializer):
    q = serializers.CharField(max_length=120, allow_blank=True, default="")
    view = serializers.ChoiceField(
        choices=["active", "history", "recovery"], required=False
    )
    coverage = serializers.ChoiceField(
        choices=["verified", "incomplete", "unverified"], required=False
    )
    layout = serializers.ChoiceField(
        choices=["multi_page", "complex", "nested", "inline", "unclassified"],
        required=False,
    )
    error_code = serializers.RegexField(r"^[a-z][a-z0-9_]{0,63}$", required=False)
    parent_job = serializers.UUIDField(required=False)
    page = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)
    state = serializers.ChoiceField(choices=BackgroundJobState.choices, required=False)
    kind = serializers.ChoiceField(choices=BackgroundJobKind.choices, required=False)
    book = serializers.UUIDField(required=False)
    automation_run = serializers.UUIDField(required=False)


class JobControlSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    action = serializers.ChoiceField(choices=JOB_CONTROL_ACTIONS)


class PreparationCommandSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    expected_updated_at = serializers.DateTimeField()


class OperationAcceptedSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    status_url = serializers.CharField()


class ProcessingAssetSerializer(serializers.ModelSerializer):
    file_available = serializers.BooleanField(read_only=True)
    download_url = serializers.CharField(read_only=True, allow_null=True)
    reader_ready = serializers.BooleanField(read_only=True)
    reader_update_available = serializers.BooleanField(read_only=True)
    active_preparation_id = serializers.UUIDField(read_only=True, allow_null=True)

    class Meta:
        model = GeneratedAsset
        fields = (
            "id",
            "asset_type",
            "status",
            "file_size",
            "checksum",
            "updated_at",
            "file_available",
            "download_url",
            "reader_ready",
            "reader_update_available",
            "active_preparation_id",
        )
        read_only_fields = fields
