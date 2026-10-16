from django.db.models import Exists, OuterRef, Subquery
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import GenericAPIView

from apps.catalog.models import Book, BookRecordType, UserBook, UserBookKindleSend
from apps.ingestion.models import BookSubmission


class BookQueryMixin(GenericAPIView):
    default_record_type = BookRecordType.DIGITAL

    def base_queryset(self):
        identity = self.request.user.pk
        if identity is None:
            raise PermissionDenied("Sign in is required.")
        owned = UserBook.objects.filter(book=OuterRef("pk"), user_id=identity).order_by("-created_at")
        kindle_sent = UserBookKindleSend.objects.filter(book=OuterRef("pk"), user_id=identity).order_by("-created_at")
        latest_submission = BookSubmission.objects.filter(linked_book=OuterRef("pk"), submitter_id=identity).order_by("-created_at").values("created_at")[:1]
        return (
            Book.objects.prefetch_related(
                "book_contributors__contributor",
                "book_series__series",
                "book_categories__category",
                "generated_assets",
                "source_urls",
            )
            .annotate(
                is_in_my_books=Exists(owned),
                user_owns_book=Exists(owned),
                my_books_added_at=Subquery(owned.values("created_at")[:1]),
                has_sent_to_kindle=Exists(kindle_sent),
                user_kindle_sent_at=Subquery(kindle_sent.values("created_at")[:1]),
                latest_submission_at=Subquery(latest_submission),
            )
            .defer(
                "summary",
                "raw_scraped_metadata",
                "raw_scrape_payload",
                "main_content_html",
                "book_info_html",
                "dedication_html",
                "toc",
                "content_items",
            )
            .filter(deleted_at__isnull=True)
        )

    def get_queryset(self):
        from .shared import filtered_book_queryset

        return filtered_book_queryset(self.base_queryset(), self.request, default_record_type=self.default_record_type)
