from datetime import UTC, datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from rest_framework import serializers

from apps.common.validation import reject_unknown_fields
from apps.ingestion.models import CatalogAutomationFrequency
from apps.processing.automation_models import AutomationRun, SourceAutomation


class AutomationSerializer(serializers.ModelSerializer):
    first_run_local = serializers.SerializerMethodField()
    run_as_name = serializers.CharField(source="run_as.display_name", read_only=True)

    def get_first_run_local(self, instance) -> str:
        return instance.first_run_at.astimezone(ZoneInfo(instance.time_zone)).strftime(
            "%Y-%m-%dT%H:%M"
        )

    class Meta:
        model = SourceAutomation
        fields = (
            "id",
            "name",
            "enabled",
            "frequency",
            "first_run_local",
            "time_zone",
            "next_run_at",
            "source_max_pages",
            "processing_limit",
            "run_as_name",
            "updated_at",
        )
        read_only_fields = fields


def validated_local_start(values):
    try:
        zone = ZoneInfo(values["time_zone"])
        local = datetime.strptime(values["first_run_local"], "%Y-%m-%dT%H:%M").replace(
            tzinfo=zone, fold=0
        )
    except (ValueError, ZoneInfoNotFoundError):
        raise serializers.ValidationError(
            {"first_run_local": "Choose a valid local time and IANA time zone."}
        ) from None
    if local.astimezone(UTC).astimezone(zone).replace(tzinfo=None) != local.replace(
        tzinfo=None
    ):
        raise serializers.ValidationError(
            {
                "first_run_local": "This local time is skipped by a daylight saving change. Choose another time."
            }
        )
    return local


class AutomationCommandSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    enabled = serializers.BooleanField(default=False)
    frequency = serializers.ChoiceField(choices=CatalogAutomationFrequency.choices)
    first_run_local = serializers.CharField(max_length=16)
    time_zone = serializers.CharField(max_length=64)
    source_max_pages = serializers.IntegerField(min_value=1, max_value=200, default=20)
    processing_limit = serializers.IntegerField(min_value=0, max_value=100, default=0)

    def validate(self, attrs):
        reject_unknown_fields(self)
        start = validated_local_start(attrs)
        instance = self.context.get("automation")
        unchanged = instance is not None and (
            instance.first_run_at == start
            and instance.time_zone == attrs["time_zone"]
            and instance.frequency == attrs["frequency"]
        )
        if not unchanged and start <= timezone.now():
            raise serializers.ValidationError(
                {"first_run_local": "Choose a future first run time."}
            )
        return {**attrs, "first_run_at": start}


class AutomationCreateSerializer(AutomationCommandSerializer):
    operation_id = serializers.UUIDField()


class AutomationUpdateSerializer(AutomationCommandSerializer):
    expected_updated_at = serializers.DateTimeField()


class AutomationRunSerializer(serializers.ModelSerializer):
    processing_count = serializers.IntegerField(read_only=True)
    processing_active = serializers.IntegerField(read_only=True)
    processing_attention = serializers.IntegerField(read_only=True)
    processing_succeeded = serializers.IntegerField(read_only=True)
    processing_rejected = serializers.IntegerField(read_only=True)
    job_state = serializers.CharField(
        source="job.state", allow_null=True, read_only=True, default=None
    )

    class Meta:
        model = AutomationRun
        fields = (
            "id",
            "due_at",
            "state",
            "error_code",
            "job_id",
            "job_state",
            "processing_limit",
            "processing_count",
            "processing_active",
            "processing_attention",
            "processing_succeeded",
            "processing_rejected",
            "missed_occurrences",
            "created_at",
        )
        read_only_fields = fields
