import csv
from io import StringIO

from rest_framework import serializers

from apps.ingestion.models import SubmissionInputType


def present_status(value):
    return "stopped" if value == "cancelled" else value


class SubmissionBatchCreateSerializer(serializers.Serializer):
    input_type = serializers.ChoiceField(choices=SubmissionInputType.choices, required=False)
    content = serializers.CharField(required=False, allow_blank=True)
    entries = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=False)
    auto_process = serializers.BooleanField(default=True)

    def validate(self, attrs):
        parsed_entries = []
        entries = attrs.get("entries") or []
        if entries:
            for raw_value in entries:
                value = raw_value.strip()
                if value:
                    parsed_entries.append({"kind": "url" if value.startswith("http") else "title", "value": value})
        else:
            input_type = attrs.get("input_type")
            content = attrs.get("content", "").strip()
            if not input_type:
                raise serializers.ValidationError({"input_type": "This field is required when entries are not supplied."})
            if not content:
                raise serializers.ValidationError({"content": "At least one submission value is required."})
            if input_type in {SubmissionInputType.URL, SubmissionInputType.TITLE}:
                for line in content.splitlines():
                    value = line.strip()
                    if value:
                        parsed_entries.append({"kind": input_type, "value": value})
            else:
                reader = csv.DictReader(StringIO(content))
                for row in reader:
                    raw_value = row.get("url") or row.get("title") or row.get("query")
                    if not raw_value:
                        raw_value = next((value for value in row.values() if value), "")
                    if raw_value:
                        value = raw_value.strip()
                        parsed_entries.append({"kind": "url" if value.startswith("http") else "title", "value": value})

        if not parsed_entries:
            raise serializers.ValidationError({"entries": "No usable submission entries were found."})
        attrs["parsed_entries"] = parsed_entries
        return attrs


class BulkIdsSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.UUIDField(), allow_empty=False, max_length=200)


__all__ = ["BulkIdsSerializer", "SubmissionBatchCreateSerializer", "present_status"]
