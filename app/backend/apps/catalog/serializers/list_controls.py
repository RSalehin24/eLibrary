from unicodedata import category

from rest_framework import serializers

from apps.common.validation import reject_unknown_fields


class BookListControlParametersSerializer(serializers.Serializer):
    slugs = serializers.ListField(
        child=serializers.CharField(max_length=255, trim_whitespace=False),
        min_length=1,
        max_length=100,
    )

    def validate_slugs(self, values):
        if any(
            any(
                character not in "_-" and category(character)[0] not in "LMN"
                for character in value
            )
            for value in values
        ):
            raise serializers.ValidationError("Choose valid book identifiers.")
        return list(dict.fromkeys(values))

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes


class BookListControlSerializer(serializers.Serializer):
    slug = serializers.CharField()
    saved = serializers.BooleanField()
    can_send_kindle = serializers.BooleanField()


class BookListControlsSerializer(serializers.Serializer):
    entries = BookListControlSerializer(many=True)
