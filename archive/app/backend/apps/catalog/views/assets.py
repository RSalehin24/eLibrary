import hashlib

from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Book, GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType
from apps.catalog.serializers import BookDetailSerializer, EpubAssetReplaceSerializer
from apps.common.permissions import CanEditMetadata


class BookEpubReplaceView(APIView):
    permission_classes = [CanEditMetadata]

    def post(self, request, slug):
        book = get_object_or_404(Book.objects.prefetch_related("generated_assets", "source_urls", "processing_jobs").filter(deleted_at__isnull=True), slug=slug)
        self.check_object_permissions(request, book)
        serializer = EpubAssetReplaceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        upload = serializer.validated_data["file"]

        content = upload.read()
        asset, _ = GeneratedAsset.objects.get_or_create(book=book, asset_type=GeneratedAssetType.EPUB)
        if asset.file and asset.file.name:
            asset.file.delete(save=False)
        asset.status = GeneratedAssetStatus.READY
        asset.content_type = upload.content_type or "application/epub+zip"
        asset.file_size = len(content)
        asset.checksum = hashlib.sha256(content).hexdigest()
        asset.source_job = None
        asset.legacy_path = ""
        asset.file.save(f"{book.title}.epub", ContentFile(content), save=False)
        asset.storage_path = asset.file.name
        asset.save(update_fields=["status", "content_type", "file_size", "checksum", "source_job", "legacy_path", "file", "storage_path", "updated_at"])
        book.refresh_from_db()
        return Response(BookDetailSerializer(book, context={"request": request}).data)


class BookRegenerateView(APIView):
    permission_classes = [CanEditMetadata]

    def post(self, request, slug):
        from apps.catalog import views as catalog_views

        book = get_object_or_404(Book.objects.prefetch_related("generated_assets", "source_urls", "processing_jobs").filter(deleted_at__isnull=True), slug=slug)
        self.check_object_permissions(request, book)
        try:
            job, created = catalog_views.queue_reprocess_book(book, actor=request.user)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        book.refresh_from_db()
        return Response(
            {
                "book": BookDetailSerializer(book, context={"request": request}).data,
                "job": {
                    "id": str(job.id),
                    "job_type": job.job_type,
                    "status": job.status,
                    "queue_name": job.queue_name,
                    "retry_count": job.retry_count,
                    "last_error": job.last_error,
                    "created_at": job.created_at,
                    "started_at": job.started_at,
                    "finished_at": job.finished_at,
                },
                "created": created,
            },
            status=status.HTTP_202_ACCEPTED,
        )
