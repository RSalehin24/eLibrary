from rest_framework import serializers


class SourceVerificationSerializer(serializers.Serializer):
    validator_version = serializers.IntegerField(default=1)
    classification = serializers.CharField(default="unknown_layout")
    reading_content = serializers.BooleanField(default=False)
    verified = serializers.BooleanField()
    source_pages = serializers.IntegerField()
    fetched_pages = serializers.IntegerField()
    expected_chapters = serializers.IntegerField()
    collected_chapters = serializers.IntegerField()
    issues = serializers.ListField(child=serializers.CharField())
