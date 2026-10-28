from typing import ClassVar

from rest_framework import serializers

from apps.catalog.models import (
    Book,
    ContributorRole,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.catalog.services import normalize_book_contributors
from apps.common.permissions import (
    user_can_view_book_cover,
)
from apps.common.url_utils import public_api_url
from apps.ingestion.services.normalization import (
    looks_like_contributor_name,
)

from .common import asset_exists, serialize_source_record


class BookListSerializer(serializers.ModelSerializer):
    authors = serializers.SerializerMethodField()
    translators = serializers.SerializerMethodField()
    compilers = serializers.SerializerMethodField()
    editors = serializers.SerializerMethodField()
    contributors = serializers.SerializerMethodField()
    series = serializers.SerializerMethodField()
    categories = serializers.SerializerMethodField()
    cover_download_url = serializers.SerializerMethodField()
    latest_submission_at = serializers.SerializerMethodField()
    is_in_my_books = serializers.SerializerMethodField()
    my_books_added_at = serializers.SerializerMethodField()
    primary_source = serializers.SerializerMethodField()
    publisher = serializers.CharField(read_only=True)
    is_compilation = serializers.BooleanField(read_only=True)
    language = serializers.CharField(read_only=True)
    has_epub_asset = serializers.SerializerMethodField()
    has_sent_to_kindle = serializers.SerializerMethodField()
    user_kindle_sent_at = serializers.SerializerMethodField()

    class Meta:
        model = Book
        fields: ClassVar = [
            "id",
            "catalog_code",
            "title",
            "slug",
            "state",
            "authors",
            "translators",
            "compilers",
            "editors",
            "contributors",
            "series",
            "categories",
            "publisher",
            "is_compilation",
            "language",
            "cover_download_url",
            "latest_submission_at",
            "is_in_my_books",
            "my_books_added_at",
            "primary_source",
            "created_at",
            "has_epub_asset",
            "has_sent_to_kindle",
            "user_kindle_sent_at",
        ]

    def relation_contributors(self, obj):
        payload = []
        for relation in obj.book_contributors.all():
            if looks_like_contributor_name(
                relation.contributor.name, role=relation.role
            ):
                payload.append(
                    {"name": relation.contributor.name, "role": relation.role}
                )
        return payload

    def get_contributors(self, obj):
        if not hasattr(obj, "_normalized_contributors"):
            obj._normalized_contributors = normalize_book_contributors(
                self.relation_contributors(obj)
            )
        return obj._normalized_contributors

    def get_authors(self, obj):
        return [
            entry["name"]
            for entry in self.get_contributors(obj)
            if entry["role"] == ContributorRole.AUTHOR
        ]

    def get_translators(self, obj):
        return [
            entry["name"]
            for entry in self.get_contributors(obj)
            if entry["role"] == ContributorRole.TRANSLATOR
        ]

    def get_compilers(self, obj):
        return [
            entry["name"]
            for entry in self.get_contributors(obj)
            if entry["role"] == ContributorRole.COMPILER
        ]

    def get_editors(self, obj):
        return [
            entry["name"]
            for entry in self.get_contributors(obj)
            if entry["role"] == ContributorRole.EDITOR
        ]

    def get_series(self, obj):
        return [rel.series.name for rel in obj.book_series.all()]

    def get_categories(self, obj):
        return [rel.category.name for rel in obj.book_categories.all()]

    def get_cover_download_url(self, obj):
        request = self.context.get("request")
        if request is not None and not user_can_view_book_cover(request.user, obj):
            return ""
        cover = next(
            (
                asset
                for asset in obj.generated_assets.all()
                if asset.asset_type == GeneratedAssetType.COVER
                and asset.status == GeneratedAssetStatus.READY
                and asset_exists(asset)
            ),
            None,
        )
        if not cover:
            return ""
        return public_api_url(
            "access-book-asset-download",
            kwargs={"slug": obj.slug, "asset_type": "cover"},
            request=request,
        )

    def get_latest_submission_at(self, obj):
        return getattr(obj, "latest_submission_at", None)

    def get_is_in_my_books(self, obj):
        return bool(getattr(obj, "is_in_my_books", False))

    def get_my_books_added_at(self, obj):
        return getattr(obj, "my_books_added_at", None)

    def get_has_sent_to_kindle(self, obj):
        return bool(getattr(obj, "has_sent_to_kindle", False))

    def get_user_kindle_sent_at(self, obj):
        return getattr(obj, "user_kindle_sent_at", None)

    serialize_source_record = staticmethod(serialize_source_record)

    def get_primary_source(self, obj):
        sources = list(obj.source_urls.all())
        if not sources:
            return None
        primary = next((source for source in sources if source.is_primary), sources[0])
        return self.serialize_source_record(primary)

    def get_has_epub_asset(self, obj):
        return obj.generated_assets.filter(
            asset_type=GeneratedAssetType.EPUB,
            status=GeneratedAssetStatus.READY,
        ).exists()
