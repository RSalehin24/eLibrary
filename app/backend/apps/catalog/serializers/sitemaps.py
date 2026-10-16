from rest_framework import serializers


class SitemapBatchSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(
        choices=("books", "contributors", "categories", "series", "collections")
    )
    pages = serializers.IntegerField(min_value=0)


class SitemapEntrySerializer(serializers.Serializer):
    slug = serializers.CharField()
    updated_at = serializers.DateTimeField()
