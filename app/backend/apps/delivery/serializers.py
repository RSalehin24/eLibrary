from django.core.exceptions import ValidationError as DjangoValidationError
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from apps.accounts.kindle import MAX_KINDLE_RECIPIENTS, normalize_kindle_addresses
from apps.processing.job_models import BackgroundJob
from apps.processing.job_serializers import BackgroundBookSerializer


class KindleRequestSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    expected_updated_at = serializers.DateTimeField()
    recipients = serializers.ListField(
        child=serializers.EmailField(), min_length=1, max_length=MAX_KINDLE_RECIPIENTS
    )

    def validate_recipients(self, values):
        try:
            return normalize_kindle_addresses(values)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages)) from error


class KindleOptionsSerializer(serializers.Serializer):
    book = BackgroundBookSerializer()
    asset_revision = serializers.DateTimeField()
    recipients = serializers.ListField(child=serializers.EmailField())
    sender_email = serializers.CharField(allow_blank=True)
    configured = serializers.BooleanField()
    max_attachment_bytes = serializers.IntegerField()


class KindleRecipientSerializer(serializers.Serializer):
    address = serializers.EmailField()
    outcome = serializers.ChoiceField(
        choices=["accepted", "rejected", "uncertain", "not_sent", "pending"]
    )


def recipient_outcomes(job):
    accepted = set(job.checkpoint.get("accepted", []))
    terminal = job.state in {"failed", "cancelled", "succeeded"}
    entries = []
    for index, address in enumerate(job.input.get("recipients", [])):
        outcome = "not_sent" if terminal else "pending"
        if index in accepted:
            outcome = "accepted"
        elif job.state == "needs_attention" and index == job.checkpoint.get(
            "sending_index"
        ):
            outcome = "uncertain"
        elif job.state == "failed" and index == job.checkpoint.get("rejected_index"):
            outcome = "rejected"
        entries.append({"address": address, "outcome": outcome})
    return entries


class KindleOperationSerializer(serializers.ModelSerializer):
    book = BackgroundBookSerializer(read_only=True)
    recipients = serializers.SerializerMethodField()
    can_cancel = serializers.SerializerMethodField()

    @extend_schema_field(KindleRecipientSerializer(many=True))
    def get_recipients(self, job) -> list[dict[str, str]]:
        return recipient_outcomes(job)

    def get_can_cancel(self, job) -> bool:
        return (
            job.state in {"queued", "running", "retry_wait", "paused"}
            and job.requested_action != "cancel"
        )

    class Meta:
        model = BackgroundJob
        fields = (
            "id",
            "book",
            "state",
            "requested_action",
            "recipients",
            "can_cancel",
            "error_code",
            "created_at",
            "updated_at",
            "finished_at",
        )
        read_only_fields = fields


class KindleCollectionSerializer(serializers.Serializer):
    entries = KindleOperationSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()


class KindleCancelSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
