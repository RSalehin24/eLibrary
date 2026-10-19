from rest_framework import serializers

NESTED_SOURCE_LAYOUTS = (
    "lesson_topic_nested",
    "mixed_lessons_and_topics",
    "sectioned_flat_lessons",
    "sectioned_lesson_topic_nested",
    "sectioned_mixed_lessons_and_topics",
)
INLINE_SOURCE_LAYOUTS = ("single_page_heading_split", "single_page_flow_no_toc")


def source_layout(snapshot):
    structure = snapshot.get("manifest", {}).get("source_structure", {})
    if not structure:
        return None
    total = int(structure.get("source_total_pages", 0))
    return {
        "structure_type": str(structure.get("type", ""))[:64],
        "multi_page": bool(structure.get("has_paginated_toc")) or total > 1,
        "contents_pages": total,
        "collected_contents_pages": int(structure.get("fetched_total_pages", 0)),
        "contents_incomplete": bool(structure.get("toc_incomplete")),
    }


class SourceLayoutSerializer(serializers.Serializer):
    structure_type = serializers.CharField()
    multi_page = serializers.BooleanField()
    contents_pages = serializers.IntegerField(min_value=0)
    collected_contents_pages = serializers.IntegerField(min_value=0)
    contents_incomplete = serializers.BooleanField()
