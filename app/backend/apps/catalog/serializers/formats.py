from rest_framework import serializers

BOOK_FORMAT_FIELDS = (
    "edition",
    "language",
    "publisher",
    "is_compilation",
)


class BookFormatSerializer(serializers.Serializer):
    edition = serializers.CharField(max_length=120, allow_blank=True, required=False)
    language = serializers.RegexField(
        r"^[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$",
        max_length=16,
        allow_blank=True,
        required=False,
    )
    publisher = serializers.CharField(max_length=255, allow_blank=True, required=False)
    is_compilation = serializers.BooleanField(required=False)
