from rest_framework import serializers

from apps.ingestion.models import (
    CatalogAutomationSettings,
    CatalogCurationMode,
    CatalogCurationRun,
    SourceCatalogEntry,
    SourceCatalogRefreshState,
)
from apps.ingestion.services.curation import next_catalog_automation_run_at

from .common import present_status


class SourceCatalogEntrySnapshotSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    author_line = serializers.CharField(allow_blank=True)
    categories = serializers.CharField(allow_blank=True)
    source_url = serializers.URLField()
    created_at = serializers.DateTimeField()
    last_seen_at = serializers.DateTimeField()
    curation_status = serializers.CharField()
    local_book_slug = serializers.CharField(allow_blank=True)
    local_book_title = serializers.CharField(allow_blank=True)
    local_book_state = serializers.CharField(allow_blank=True)
    latest_submission_status = serializers.CharField(allow_blank=True)
    latest_job_status = serializers.CharField(allow_blank=True)
    latest_job_error = serializers.CharField(allow_blank=True)
    activity_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)

    def to_representation(self, instance):
        payload = super().to_representation(instance)
        for field in ("latest_submission_status", "latest_job_status", "curation_status"):
            payload[field] = present_status(payload.get(field, ""))
        return payload


class CatalogCurationRunSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)

    class Meta:
        model = CatalogCurationRun
        fields = [
            "id",
            "trigger",
            "mode",
            "status",
            "refresh_catalog",
            "refresh_max_pages",
            "task_id",
            "queue_name",
            "retry_count",
            "cancel_requested",
            "requested_by_email",
            "summary",
            "last_error",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
        ]

    def get_status(self, obj):
        return present_status(obj.status)


class CatalogCurationRunCreateSerializer(serializers.Serializer):
    mode = serializers.ChoiceField(choices=CatalogCurationMode.choices, default=CatalogCurationMode.PENDING)
    refresh_catalog = serializers.BooleanField(default=True)
    refresh_max_pages = serializers.IntegerField(required=False, min_value=1, max_value=80, default=80)


class SourceCatalogRefreshStateSerializer(serializers.ModelSerializer):
    requested_by_email = serializers.EmailField(source="requested_by.email", read_only=True)

    class Meta:
        model = SourceCatalogRefreshState
        fields = [
            "status",
            "max_pages",
            "task_id",
            "queue_name",
            "retry_count",
            "refreshed_entries",
            "last_error",
            "requested_by_email",
            "created_at",
            "updated_at",
            "started_at",
            "finished_at",
        ]


class CatalogAutomationSettingsSerializer(serializers.ModelSerializer):
    next_run_at = serializers.SerializerMethodField()

    class Meta:
        model = CatalogAutomationSettings
        fields = ["enabled", "daily_run_time", "frequency", "mode", "refresh_max_pages", "next_run_at"]

    def get_next_run_at(self, obj):
        return next_catalog_automation_run_at(obj)


class CatalogAutomationSettingsUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CatalogAutomationSettings
        fields = ["enabled", "daily_run_time", "frequency", "mode", "refresh_max_pages"]


__all__ = [
    "CatalogAutomationSettingsSerializer",
    "CatalogAutomationSettingsUpdateSerializer",
    "CatalogCurationRunCreateSerializer",
    "CatalogCurationRunSerializer",
    "SourceCatalogEntrySnapshotSerializer",
    "SourceCatalogRefreshStateSerializer",
]
