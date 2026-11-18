from rest_framework import serializers

from apps.catalog.models import Category, Contributor, Series
from apps.common.text import clean_entity_display_text


class CategoryListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    book_count = serializers.IntegerField(read_only=True)
    digital_book_count = serializers.IntegerField(read_only=True)
    manual_book_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = [
            "id",
            "catalog_code",
            "name",
            "slug",
            "book_count",
            "digital_book_count",
            "manual_book_count",
            "created_at",
        ]

    def get_name(self, obj):
        return clean_entity_display_text(obj.name)


class ContributorListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    book_count = serializers.IntegerField(read_only=True)
    digital_book_count = serializers.IntegerField(read_only=True)
    manual_book_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Contributor
        fields = [
            "id",
            "catalog_code",
            "name",
            "slug",
            "book_count",
            "digital_book_count",
            "manual_book_count",
            "created_at",
        ]

    def get_name(self, obj):
        return clean_entity_display_text(obj.name)


class SeriesListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    book_count = serializers.IntegerField(read_only=True)
    digital_book_count = serializers.IntegerField(read_only=True)
    manual_book_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Series
        fields = [
            "id",
            "catalog_code",
            "name",
            "slug",
            "book_count",
            "digital_book_count",
            "manual_book_count",
            "created_at",
        ]

    def get_name(self, obj):
        return clean_entity_display_text(obj.name)
