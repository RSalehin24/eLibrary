from rest_framework import serializers

from apps.common.validation import reject_unknown_fields, reject_unknown_input
from apps.processing.job_serializers import JOB_CONTROL_ACTIONS
from apps.processing.jobs.source_bulk_controls import SOURCE_BULK_ACTIONS

BULK_JOB_CONTROL_ACTIONS = (*JOB_CONTROL_ACTIONS, *SOURCE_BULK_ACTIONS)


class BulkJobControlEntrySerializer(serializers.Serializer):
    id = serializers.UUIDField()
    expected_updated_at = serializers.DateTimeField()
    expected_book_updated_at = serializers.DateTimeField(required=False)

    def to_internal_value(self, data):
        reject_unknown_input(self, data)
        return super().to_internal_value(data)


class BulkJobControlSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    action = serializers.ChoiceField(choices=BULK_JOB_CONTROL_ACTIONS)
    entries: serializers.ListSerializer[dict[str, object]] = serializers.ListSerializer(
        child=BulkJobControlEntrySerializer(), min_length=1, max_length=100
    )

    def validate(self, values):
        reject_unknown_fields(self)
        identifiers = [entry["id"] for entry in values["entries"]]
        if len(set(identifiers)) != len(identifiers):
            raise serializers.ValidationError({"entries": "Select each job only once."})
        if values["action"] in {"recreate_source", "archive_book"} and any(
            not entry.get("expected_book_updated_at") for entry in values["entries"]
        ):
            raise serializers.ValidationError(
                {"entries": "Book actions require every displayed book revision."}
            )
        return values


class BulkJobControlOutcomeSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    outcome = serializers.ChoiceField(
        choices=["accepted", "conflict", "not_found", "forbidden", "rejected"]
    )
    code = serializers.CharField(allow_blank=True)


class BulkJobControlResultSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    entries = BulkJobControlOutcomeSerializer(many=True)
