from urllib.parse import unquote, urlparse

from rest_framework import serializers

from apps.catalog.models import Book, ContributorRole, GeneratedAssetStatus, GeneratedAssetType
from apps.catalog.services import normalize_book_contributors
from apps.common.permissions import user_can_view_book_cover
from apps.common.url_utils import public_api_url
from apps.ingestion.services.normalization import (
    clean_extracted_dedication_html,
    combined_front_matter_html,
    extract_front_matter_entries,
    looks_like_contributor_name,
    merge_front_matter_html_parts,
    split_contributor_value,
)

from .common import GeneratedAssetSerializer, asset_exists


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
    binding = serializers.SerializerMethodField()
    publisher = serializers.CharField(source="manual_publisher", read_only=True)
    price = serializers.DecimalField(source="manual_price", read_only=True, max_digits=10, decimal_places=2, allow_null=True)
    is_compilation = serializers.BooleanField(source="manual_is_compilation", read_only=True)

    class Meta:
        model = Book
        fields = [
            "id",
            "catalog_code",
            "record_type",
            "title",
            "slug",
            "state",
            "review_state",
            "authors",
            "translators",
            "compilers",
            "editors",
            "contributors",
            "series",
            "categories",
            "binding",
            "publisher",
            "price",
            "is_compilation",
            "cover_download_url",
            "latest_submission_at",
            "is_in_my_books",
            "my_books_added_at",
            "primary_source",
            "created_at",
        ]

    def relation_contributors(self, obj):
        payload = []
        for relation in obj.book_contributors.all():
            if looks_like_contributor_name(relation.contributor.name, role=relation.role):
                payload.append({"name": relation.contributor.name, "role": relation.role})
        return payload

    def get_contributors(self, obj):
        if not hasattr(obj, '_normalized_contributors'):
            obj._normalized_contributors = normalize_book_contributors(self.relation_contributors(obj))
        return obj._normalized_contributors

    def get_authors(self, obj):
        return [entry["name"] for entry in self.get_contributors(obj) if entry["role"] == ContributorRole.AUTHOR]

    def get_translators(self, obj):
        return [entry["name"] for entry in self.get_contributors(obj) if entry["role"] == ContributorRole.TRANSLATOR]

    def get_compilers(self, obj):
        return [entry["name"] for entry in self.get_contributors(obj) if entry["role"] == ContributorRole.COMPILER]

    def get_editors(self, obj):
        return [entry["name"] for entry in self.get_contributors(obj) if entry["role"] == ContributorRole.EDITOR]

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

    def serialize_source_record(self, source):
        url = source.normalized_source_url or source.source_url
        parsed = urlparse(url)
        return {
            "url": url,
            "display_url": unquote(url),
            "display_path": unquote(parsed.path).strip("/") or parsed.netloc,
            "source_title": source.source_title,
            "source_type": source.source_type,
            "site": parsed.netloc,
            "is_primary": source.is_primary,
        }

    def get_primary_source(self, obj):
        sources = list(obj.source_urls.all())
        if not sources:
            return None
        primary = next((source for source in sources if source.is_primary), sources[0])
        return self.serialize_source_record(primary)

    def get_binding(self, obj):
        return obj.get_manual_binding_display() if obj.manual_binding else ""


class BookDetailSerializer(BookListSerializer):
    assets = GeneratedAssetSerializer(source="generated_assets", many=True, read_only=True)
    source_urls = serializers.SerializerMethodField()
    source_records = serializers.SerializerMethodField()
    front_matter = serializers.SerializerMethodField()
    latest_processing_job = serializers.SerializerMethodField()
    book_info_html = serializers.SerializerMethodField()
    dedication_html = serializers.SerializerMethodField()
    toc = serializers.JSONField()
    empty_chapters = serializers.SerializerMethodField()
    raw_provenance = serializers.SerializerMethodField()

    class Meta(BookListSerializer.Meta):
        fields = BookListSerializer.Meta.fields + [
            "assets",
            "source_urls",
            "source_records",
            "front_matter",
            "latest_processing_job",
            "book_info_html",
            "dedication_html",
            "toc",
            "empty_chapters",
            "empty_chapters_count",
            "metadata_last_reviewed_at",
            "raw_provenance",
        ]

    def build_contributors_payload(self, obj):
        front_matter_html = combined_front_matter_html(obj.book_info_html, obj.main_content_html)
        payload = list(self.relation_contributors(obj))
        for entry in extract_front_matter_entries(front_matter_html):
            if entry["role"]:
                for name in split_contributor_value(entry["value"], role=entry["role"]):
                    payload.append({"name": name, "role": entry["role"]})
        return normalize_book_contributors(payload)

    def get_authors(self, obj):
        return [entry["name"] for entry in self.build_contributors_payload(obj) if entry["role"] == ContributorRole.AUTHOR]

    def get_contributors(self, obj):
        return self.build_contributors_payload(obj)

    def get_source_urls(self, obj):
        return [source.normalized_source_url for source in obj.source_urls.all()]

    def get_source_records(self, obj):
        return [self.serialize_source_record(source) for source in obj.source_urls.all()]

    def get_front_matter(self, obj):
        html = combined_front_matter_html(obj.book_info_html, obj.main_content_html)
        return [
            {
                "key": entry["key"],
                "label": entry["label"],
                "value": entry["value"],
                "role": entry["role"],
            }
            for entry in extract_front_matter_entries(html)
            if not entry["role"]
        ]

    def get_book_info_html(self, obj):
        return merge_front_matter_html_parts(obj.book_info_html)

    def get_dedication_html(self, obj):
        return clean_extracted_dedication_html(obj.dedication_html)

    def get_latest_processing_job(self, obj):
        job = obj.processing_jobs.first()
        if not job:
            return None
        return {
            "id": str(job.id),
            "job_type": job.job_type,
            "status": job.status,
            "queue_name": job.queue_name,
            "retry_count": job.retry_count,
            "last_error": job.last_error,
            "created_at": job.created_at,
            "started_at": job.started_at,
            "finished_at": job.finished_at,
        }

    def get_raw_provenance(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated and request.user.is_staff:
            return {
                "raw_scraped_metadata": obj.raw_scraped_metadata,
                "raw_scrape_payload": obj.raw_scrape_payload,
            }
        return {}

    @staticmethod
    def _collect_empty_toc_nodes(nodes):
        """Recursively collect non-section TOC entries with no content."""
        result = []
        for node in nodes or []:
            node_type = node.get("type", "lesson")
            if node_type != "section" and node.get("has_content") is not True:
                result.append({
                    "title": node.get("title", ""),
                    "type": node_type,
                    "has_content": node.get("has_content"),  # False or None
                    "source_url": node.get("source_url", ""),
                    "path": node.get("path", []),
                })
            result.extend(
                BookDetailSerializer._collect_empty_toc_nodes(node.get("children", []))
            )
        return result

    def get_empty_chapters(self, obj):
        return self._collect_empty_toc_nodes(obj.toc)
