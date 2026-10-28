from rest_framework import serializers

from apps.access.models import PermissionScope
from apps.catalog.models import (
    ContributorRole,
)
from apps.catalog.services import normalize_book_contributors
from apps.common.permissions import (
    user_can_launch_reader,
    user_can_view_preview_html,
    user_has_scope,
)
from apps.ingestion.services.normalization import (
    clean_extracted_dedication_html,
    combined_front_matter_html,
    extract_front_matter_entries,
    merge_front_matter_html_parts,
    split_contributor_value,
)

from .book_lists import BookListSerializer
from .common import GeneratedAssetSerializer
from .toc import collect_empty_toc_nodes


class BookDetailSerializer(BookListSerializer):
    assets = GeneratedAssetSerializer(
        source="generated_assets", many=True, read_only=True
    )
    source_urls = serializers.SerializerMethodField()
    source_records = serializers.SerializerMethodField()
    front_matter = serializers.SerializerMethodField()
    latest_processing_job = serializers.SerializerMethodField()
    book_info_html = serializers.SerializerMethodField()
    dedication_html = serializers.SerializerMethodField()
    toc = serializers.JSONField()
    empty_chapters = serializers.SerializerMethodField()
    raw_provenance = serializers.SerializerMethodField()
    can_launch_reader = serializers.SerializerMethodField()
    can_view_preview_html = serializers.SerializerMethodField()

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
            "raw_provenance",
            "can_launch_reader",
            "can_view_preview_html",
        ]

    def get_can_launch_reader(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return user_can_launch_reader(request.user, obj)

    def get_can_view_preview_html(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return user_can_view_preview_html(request.user, obj)

    def build_contributors_payload(self, obj):
        front_matter_html = combined_front_matter_html(
            obj.book_info_html, obj.main_content_html
        )
        payload = list(self.relation_contributors(obj))
        for entry in extract_front_matter_entries(front_matter_html):
            if entry["role"]:
                for name in split_contributor_value(entry["value"], role=entry["role"]):
                    payload.append({"name": name, "role": entry["role"]})
        return normalize_book_contributors(payload)

    def get_authors(self, obj):
        return [
            entry["name"]
            for entry in self.build_contributors_payload(obj)
            if entry["role"] == ContributorRole.AUTHOR
        ]

    def get_contributors(self, obj):
        return self.build_contributors_payload(obj)

    def get_source_urls(self, obj):
        request = self.context.get("request")
        if request and user_has_scope(
            request.user, [PermissionScope.VIEW_SOURCE_RECORDS], book=obj
        ):
            return [source.normalized_source_url for source in obj.source_urls.all()]
        return []

    def get_source_records(self, obj):
        request = self.context.get("request")
        if request and user_has_scope(
            request.user, [PermissionScope.VIEW_SOURCE_RECORDS], book=obj
        ):
            return [
                self.serialize_source_record(source) for source in obj.source_urls.all()
            ]
        return []

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

    _collect_empty_toc_nodes = staticmethod(collect_empty_toc_nodes)

    def get_empty_chapters(self, obj):
        return self._collect_empty_toc_nodes(obj.toc)


__all__ = ["BookDetailSerializer", "BookListSerializer"]
