from rest_framework import serializers


class SourceVerificationSerializer(serializers.Serializer):
    verified = serializers.BooleanField()
    source_pages = serializers.IntegerField()
    fetched_pages = serializers.IntegerField()
    expected_chapters = serializers.IntegerField()
    collected_chapters = serializers.IntegerField()
    issues = serializers.ListField(child=serializers.CharField())
