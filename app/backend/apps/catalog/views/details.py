from django.db.models import Exists, OuterRef, Subquery
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.text import slugify
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.models import PermissionScope
from apps.catalog.models import Book, MetadataReview, MetadataVersion, UserBook
from apps.catalog.serializers import BookDetailSerializer, BookMetadataUpdateSerializer, MetadataReviewDecisionSerializer, MetadataReviewSerializer
from apps.common.models import LifecycleState
from apps.common.permissions import CanEditMetadata, user_has_scope
from apps.ingestion.models import BookSubmission


class BookDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookDetailSerializer
    lookup_field = "slug"

    def get_queryset(self):
        owned = UserBook.objects.filter(book=OuterRef("pk"), user=self.request.user).order_by("-created_at")
        latest_submission = BookSubmission.objects.filter(linked_book=OuterRef("pk"), submitter=self.request.user).order_by("-created_at").values("created_at")[:1]
        return Book.objects.prefetch_related("book_contributors__contributor", "book_series__series", "book_categories__category", "generated_assets", "source_urls", "processing_jobs").annotate(is_in_my_books=Exists(owned), user_owns_book=Exists(owned), my_books_added_at=Subquery(owned.values("created_at")[:1]), latest_submission_at=Subquery(latest_submission)).filter(deleted_at__isnull=True)

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
        if not user_has_scope(request.user, [PermissionScope.METADATA_EDIT], book=book):
            raise PermissionDenied("You do not have permission to delete this book.")
        book.state = LifecycleState.SOFT_DELETED
        book.deleted_at = timezone.now()
        book.save(update_fields=["state", "deleted_at", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class MetadataVersionListView(generics.ListAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        book = get_object_or_404(Book, slug=kwargs["slug"])
        if not user_has_scope(request.user, [PermissionScope.METADATA_EDIT], book=book):
            raise PermissionDenied("You do not have permission to inspect metadata history for this book.")
        versions = MetadataVersion.objects.filter(book=book).order_by("-created_at")
        return Response([{"id": str(version.id), "source": version.source, "notes": version.notes, "created_at": version.created_at} for version in versions])


class BookMetadataUpdateView(generics.UpdateAPIView):
    permission_classes = [CanEditMetadata]
    serializer_class = BookMetadataUpdateSerializer
    lookup_field = "slug"

    def get_queryset(self):
        return Book.objects.prefetch_related("book_contributors__contributor", "book_series__series", "book_categories__category")

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop("partial", True))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        instance.refresh_from_db()
        return Response(BookDetailSerializer(instance, context={"request": request}).data)


class MetadataReviewListCreateView(generics.ListCreateAPIView):
    permission_classes = [CanEditMetadata]
    serializer_class = MetadataReviewSerializer

    def get_book(self):
        book = get_object_or_404(Book, slug=self.kwargs["slug"])
        if not user_has_scope(self.request.user, [PermissionScope.METADATA_EDIT], book=book):
            raise PermissionDenied("You do not have permission to review metadata for this book.")
        return book

    def get_queryset(self):
        return MetadataReview.objects.filter(book=self.get_book()).select_related("requested_by", "reviewer")

    def perform_create(self, serializer):
        actor = self.request.user
        book = self.get_book()
        state = serializer.validated_data.get("state", book.review_state)
        serializer.save(book=book, requested_by=actor, reviewer=actor if state != "pending" else None)
        book.review_state = state
        if state in {"approved", "rejected"}:
            book.metadata_last_reviewed_at = timezone.now()
        book.save(update_fields=["review_state", "metadata_last_reviewed_at", "updated_at"])


class MetadataReviewUpdateView(generics.UpdateAPIView):
    permission_classes = [CanEditMetadata]
    serializer_class = MetadataReviewDecisionSerializer
    queryset = MetadataReview.objects.select_related("book", "requested_by", "reviewer")

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        if not user_has_scope(request.user, [PermissionScope.METADATA_EDIT], book=instance.book):
            raise PermissionDenied("You do not have permission to update metadata review for this book.")
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        state = serializer.validated_data.get("state", instance.state)
        instance.reviewer = request.user
        instance.save(update_fields=["reviewer", "updated_at"])
        instance.book.review_state = state
        if state in {"approved", "rejected"}:
            instance.book.metadata_last_reviewed_at = timezone.now()
        instance.book.save(update_fields=["review_state", "metadata_last_reviewed_at", "updated_at"])
        return Response(MetadataReviewSerializer(instance).data)
