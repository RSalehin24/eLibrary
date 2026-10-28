from rest_framework import serializers

from apps.common.validation import reject_unknown_fields


class SavedBookSerializer(serializers.Serializer):
    saved = serializers.BooleanField()

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes
