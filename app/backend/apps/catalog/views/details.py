from typing import ClassVar

from django.db.models import Exists, OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.models import PermissionScope
from apps.catalog.editorial.lifecycle import remove_managed_book
from apps.catalog.models import Book, MetadataVersion, UserBook, UserBookKindleSend
from apps.catalog.serializers import BookDetailSerializer
from apps.catalog.serializers.editorial import ExpectedRevisionSerializer
from apps.catalog.views.editorial import ManagedBookDetailView
from apps.common.permissions import (
    is_book_administrator,
    user_has_scope,
)
from apps.ingestion.models import BookSubmission


class BookDetailView(generics.RetrieveDestroyAPIView):
    permission_classes: ClassVar = [IsAuthenticated]
    serializer_class = BookDetailSerializer
    lookup_field = "slug"

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if "/" in kwargs.get("slug", ""):
            raise Http404

    def get_queryset(self):
        identity = self.request.user.pk
        if identity is None:
            raise PermissionDenied("Sign in is required.")
        owned = UserBook.objects.filter(book=OuterRef("pk"), user_id=identity).order_by(
            "-created_at"
        )
        kindle_sent = UserBookKindleSend.objects.filter(
            book=OuterRef("pk"), user_id=identity
        ).order_by("-created_at")
        latest_submission = (
            BookSubmission.objects.filter(
                linked_book=OuterRef("pk"), submitter_id=identity
            )
            .order_by("-created_at")
            .values("created_at")[:1]
        )
        return (
            Book.objects.prefetch_related(
                "book_contributors__contributor",
                "book_series__series",
                "book_categories__category",
                "generated_assets",
                "source_urls",
                "processing_jobs",
            )
            .annotate(
                is_in_my_books=Exists(owned),
                user_owns_book=Exists(owned),
                my_books_added_at=Subquery(owned.values("created_at")[:1]),
                has_sent_to_kindle=Exists(kindle_sent),
                user_kindle_sent_at=Subquery(kindle_sent.values("created_at")[:1]),
                latest_submission_at=Subquery(latest_submission),
            )
            .filter(deleted_at__isnull=True)
        )

    def get_object(self):
        queryset = self.get_queryset()
        slug = self.kwargs["slug"]
        book = queryset.filter(slug=slug).first()
        if book:
            self.check_object_permissions(self.request, book)
            return book
        for candidate in queryset.only("id", "title", "slug").iterator(chunk_size=200):
            if slugify(candidate.title or "", allow_unicode=True) == slug:
                book = queryset.get(pk=candidate.pk)
                self.check_object_permissions(self.request, book)
                return book
        raise Http404

    def destroy(self, request, *args, **kwargs):
        book = self.get_object()
        if not is_book_administrator(request.user):
            raise PermissionDenied("You do not have permission to delete this book.")
        values = ExpectedRevisionSerializer(data=request.data)
        values.is_valid(raise_exception=True)
        remove_managed_book(
            request.user, book.pk, values.validated_data["expected_updated_at"]
        )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MetadataVersionListView(generics.ListAPIView):
    permission_classes: ClassVar = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, slug=kwargs["slug"])
        if not user_has_scope(request.user, [PermissionScope.METADATA_EDIT], book=book):
            raise PermissionDenied(
                "You do not have permission to inspect metadata history for this book."
            )
        versions = MetadataVersion.objects.filter(book=book).order_by("-created_at")
        return Response(
            [
                {
                    "id": str(version.id),
                    "source": version.source,
                    "notes": version.notes,
                    "created_at": version.created_at,
                }
                for version in versions
            ]
        )


class BookMetadataUpdateView(ManagedBookDetailView):
    """Every served metadata URL uses the same whitelist and revision checks."""
