from __future__ import annotations

from rest_framework import serializers

from apps.catalog.models import ContributorRole
from apps.catalog.serializers.managed_entities import CatalogReferenceSerializer
from apps.common.validation import reject_unknown_fields, reject_unknown_input


class ContributorSelectionSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    role = serializers.ChoiceField(choices=ContributorRole.choices)

    def to_internal_value(self, data):
        reject_unknown_input(self, data)
        return super().to_internal_value(data)


class BookRelationshipsUpdateSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()
    edit_note = serializers.CharField(
        max_length=2000, allow_blank=True, required=False, write_only=True
    )
    contributors: serializers.ListSerializer[dict[str, object]] = (
        serializers.ListSerializer(
            child=ContributorSelectionSerializer(), max_length=100, required=False
        )
    )
    category_ids = serializers.ListField(
        child=serializers.UUIDField(), max_length=100, required=False
    )
    series_ids = serializers.ListField(
        child=serializers.UUIDField(), max_length=100, required=False
    )
    edition_of = serializers.UUIDField(allow_null=True, required=False)

    def validate(self, attributes):
        reject_unknown_fields(self)
        if not set(attributes).difference({"expected_updated_at", "edit_note"}):
            raise serializers.ValidationError(
                {"non_field_errors": "Supply relationships to update."}
            )
        for field in ("contributors", "category_ids", "series_ids"):
            entries = attributes.get(field, [])
            keys = (
                [(entry["id"], entry["role"]) for entry in entries]
                if field == "contributors"
                else entries
            )
            if len(set(keys)) != len(keys):
                raise serializers.ValidationError(
                    {field: "Select each relationship only once."}
                )
        return attributes


class ContributorReferenceSerializer(CatalogReferenceSerializer):
    role = serializers.ChoiceField(choices=ContributorRole.choices)


class BookRelationshipsSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    updated_at = serializers.DateTimeField()
    contributors = ContributorReferenceSerializer(many=True)
    categories = CatalogReferenceSerializer(many=True)
    series = CatalogReferenceSerializer(many=True)
    group_id = serializers.UUIDField(allow_null=True)
    related_editions = CatalogReferenceSerializer(many=True)
    has_more_editions = serializers.BooleanField()
