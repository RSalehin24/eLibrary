import json
import re

from rest_framework import serializers

TEXT_ANCHOR_PREFIX = "text:"


class TextBookmarkPositionSerializer(serializers.Serializer):
    chapter = serializers.IntegerField(min_value=0, max_value=9999)
    offset = serializers.IntegerField(min_value=0, max_value=32_000_000)
    quote = serializers.CharField(max_length=32, trim_whitespace=False)

    def validate_quote(self, value):
        if not value.strip():
            raise serializers.ValidationError("Choose visible text for this position.")
        return value


def text_bookmark_position(value):
    try:
        payload = json.loads(value.removeprefix(TEXT_ANCHOR_PREFIX))
    except (TypeError, ValueError) as error:
        raise serializers.ValidationError("Choose a valid text position.") from error
    if not isinstance(payload, dict) or set(payload) != {"chapter", "offset", "quote"}:
        raise serializers.ValidationError("Choose a valid text position.")
    position = TextBookmarkPositionSerializer(data=payload)
    position.is_valid(raise_exception=True)
    return position.validated_data


def normalized_bookmark_position(value):
    if value.startswith(TEXT_ANCHOR_PREFIX):
        position = text_bookmark_position(value)
        return TEXT_ANCHOR_PREFIX + json.dumps(
            position, ensure_ascii=False, separators=(",", ":")
        )
    if not re.fullmatch(r"chapter:\d+:(?:0(?:\.\d+)?|1(?:\.0+)?)", value):
        raise serializers.ValidationError("Choose a valid reading position.")
    _, chapter, fraction = value.split(":")
    return f"chapter:{int(chapter)}:{float(fraction):.4f}"


def bookmark_chapter_index(value):
    if value.startswith(TEXT_ANCHOR_PREFIX):
        return text_bookmark_position(value)["chapter"]
    return int(value.split(":")[1])
