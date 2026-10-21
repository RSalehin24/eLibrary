from rest_framework import serializers

from apps.catalog.cover_urls import book_cover_url
from apps.catalog.discovery.sorting import CATALOG_SORTS
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    ContributorRole,
)
from apps.catalog.serializers.editorial import (
    PUBLIC_EDITORIAL_FIELDS,
    ReviewedEditorialSerializer,
)
from apps.common.api_serializers import AdminPaginationSerializer
from apps.common.collection_pagination import CollectionPaginationSerializer
from apps.common.text import normalize_catalog_text


class CatalogQueryParametersSerializer(serializers.Serializer):
    q = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )

    def validate_q(self, value):
        if value and not normalize_catalog_text(value):
            raise serializers.ValidationError("Enter letters or numbers to search.")
        return value


class CatalogFilterParametersSerializer(CatalogQueryParametersSerializer):
    record_type = serializers.ChoiceField(
        choices=["all", "digital", "manual"], default="all"
    )
    ownership = serializers.ChoiceField(
        choices=["", "mine"], default="", allow_blank=True
    )
    sort = serializers.ChoiceField(choices=CATALOG_SORTS, default="", allow_blank=True)
    contributor_role = serializers.ChoiceField(
        choices=ContributorRole.choices, allow_blank=True, default=""
    )
    category = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    contributor = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    series = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    collection = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )


class ReaderPageParametersSerializer(serializers.Serializer):
    limit = serializers.IntegerField(min_value=1, max_value=100, default=24)
    cursor = serializers.CharField(
        max_length=2048, required=False, allow_blank=True, default=""
    )
    page = serializers.IntegerField(min_value=1, max_value=10000, required=False)

    def validate(self, attributes):
        if attributes.get("page") and attributes.get("cursor"):
            raise serializers.ValidationError(
                {"cursor": "Choose either page or cursor pagination."}
            )
        return attributes


class DiscoveryParametersSerializer(
    CatalogFilterParametersSerializer, ReaderPageParametersSerializer
):
    pass


class CollectionParametersSerializer(
    CatalogQueryParametersSerializer, ReaderPageParametersSerializer
):
    pass


class AdminBookParametersSerializer(CatalogFilterParametersSerializer):
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)
    page = serializers.IntegerField(min_value=1, default=1)


class PublicContributorSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="contributor.id")
    name = serializers.CharField(source="contributor.name")
    slug = serializers.CharField(source="contributor.slug")

    class Meta:
        model = BookContributor
        fields = ("id", "name", "slug", "role")


class PublicCategorySerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="category.id")
    name = serializers.CharField(source="category.name")
    slug = serializers.CharField(source="category.slug")

    class Meta:
        model = BookCategory
        fields = ("id", "name", "slug")


class PublicSeriesSerializer(serializers.ModelSerializer):
    id = serializers.UUIDField(source="series.id")
    name = serializers.CharField(source="series.name")
    slug = serializers.CharField(source="series.slug")

    class Meta:
        model = BookSeries
        fields = ("id", "name", "slug")


class PublicBookListSerializer(serializers.ModelSerializer):
    cover_url = serializers.SerializerMethodField()

    def get_cover_url(self, book) -> str | None:
        return book_cover_url(book)

    slug = serializers.CharField(read_only=True)
    language = serializers.CharField(source="manual_language")
    contributors = PublicContributorSerializer(source="book_contributors", many=True)
    categories = PublicCategorySerializer(source="book_categories", many=True)
    series = PublicSeriesSerializer(source="book_series", many=True)

    class Meta:
        model = Book
        fields: tuple[str, ...] = (
            "id",
            "title",
            "slug",
            "catalog_code",
            "language",
            "edition",
            "contributors",
            "categories",
            "series",
            "cover_url",
        )
        read_only_fields = fields


class PublicBookDetailSerializer(PublicBookListSerializer, ReviewedEditorialSerializer):
    class Meta(PublicBookListSerializer.Meta):
        fields = (
            *PublicBookListSerializer.Meta.fields,
            "summary",
            "record_type",
            "manual_publisher",
            "manual_price",
            "manual_binding",
            "manual_is_compilation",
            *PUBLIC_EDITORIAL_FIELDS,
        )
        read_only_fields = fields


class AdminBookListSerializer(PublicBookListSerializer):
    class Meta(PublicBookListSerializer.Meta):
        fields = (
            *PublicBookListSerializer.Meta.fields,
            "state",
            "review_state",
            "record_type",
        )
        read_only_fields = fields


class PublicBookCollectionSerializer(serializers.Serializer):
    entries = PublicBookListSerializer(many=True)
    next_cursor = serializers.CharField(allow_null=True)
    has_more = serializers.BooleanField()
    pagination = CollectionPaginationSerializer()


class AdminBookCollectionSerializer(serializers.Serializer):
    entries = AdminBookListSerializer(many=True)
    pagination = AdminPaginationSerializer()
