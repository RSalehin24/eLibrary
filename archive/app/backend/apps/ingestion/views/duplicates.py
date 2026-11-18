from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from apps.ingestion import views as ingestion_views
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import ReviewState
from apps.common.permissions import CanManageProcessing
from apps.ingestion.models import (
    DuplicateReview,
    DuplicateReviewStatus,
    ProcessingJob,
    SubmissionStatus,
    TitleResolutionAttempt,
)
from apps.ingestion.serializers import DuplicateReviewDecisionSerializer, DuplicateReviewSerializer
from apps.ingestion.services.submissions import fulfill_submission_with_existing_book

from .filters import apply_limit, apply_submission_origin_filter, apply_text_search
from .guards import automation_manual_creation_locked_response
from .querysets import (
    duplicate_reviews_ordered_queryset,
    related_book_list_defer_fields,
)


class DuplicateReviewListView(generics.ListAPIView):
    permission_classes = [CanManageProcessing]
    serializer_class = DuplicateReviewSerializer

    def get_queryset(self):
        queryset = DuplicateReview.objects.select_related(
            "submission",
            "submission__linked_book",
            "submission__canonical_submission",
            "submission__canonical_submission__linked_book",
            "existing_book",
        ).defer(
            *related_book_list_defer_fields(
                "submission__linked_book__",
                "submission__canonical_submission__linked_book__",
                "existing_book__",
            ),
        ).prefetch_related(
            Prefetch(
                "submission__resolution_attempts",
                queryset=TitleResolutionAttempt.objects.defer(
                    "raw_results",
                    "error_message",
                ).prefetch_related("match_candidates"),
            ),
            Prefetch(
                "submission__processing_jobs",
                queryset=ProcessingJob.objects.select_related("book").defer(
                    "payload",
                    *related_book_list_defer_fields("book__"),
                ),
            ),
            Prefetch(
                "submission__canonical_submission__resolution_attempts",
                queryset=TitleResolutionAttempt.objects.defer(
                    "raw_results",
                    "error_message",
                ).prefetch_related("match_candidates"),
            ),
            Prefetch(
                "submission__canonical_submission__processing_jobs",
                queryset=ProcessingJob.objects.select_related("book").defer(
                    "payload",
                    *related_book_list_defer_fields("book__"),
                ),
            ),
            "existing_book__book_contributors__contributor",
            "existing_book__book_series__series",
            "existing_book__book_categories__category",
            "existing_book__generated_assets",
        )
        queryset = apply_submission_origin_filter(queryset, self.request.query_params.get("origin", "").strip(), field_name="submission__origin")
        status_filter = self.request.query_params.get("status", "").strip()
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        else:
            queryset = queryset.filter(status=DuplicateReviewStatus.PENDING)
        query = self.request.query_params.get("q", "").strip()
        if query:
            queryset = apply_text_search(queryset, query, "submission__original_input", "existing_book__title", "notes")
        return apply_limit(duplicate_reviews_ordered_queryset(queryset), self.request, default_limit=40)


class DuplicateReviewResolveView(APIView):
    permission_classes = [CanManageProcessing]

    def post(self, request, pk):
        review = get_object_or_404(DuplicateReview.objects.select_related("submission", "existing_book"), pk=pk)
        serializer = DuplicateReviewDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        decision = serializer.validated_data["decision"]
        if decision == "same_book":
            decision = "confirm_existing"
        elif decision == "new_book":
            decision = "dismiss"
        review.notes = serializer.validated_data.get("notes", "")

        if decision == "confirm_existing":
            if review.existing_book.deleted_at:
                return Response({"detail": "This existing book was deleted. Recreate it instead."}, status=status.HTTP_410_GONE)
            fulfill_submission_with_existing_book(
                review.submission,
                review.existing_book,
                source="duplicate_review_confirmed",
                confidence=max(review.submission.resolution_confidence, 0.95),
                resolved_url=review.submission.resolved_url,
            )
            review.submission.duplicate_of_book = review.existing_book
            review.submission.save(update_fields=["duplicate_of_book", "updated_at"])
            review.status = DuplicateReviewStatus.CONFIRMED
        else:
            target_submission = review.submission.canonical_submission or review.submission
            update_fields = []
            if target_submission.linked_book_id and target_submission.linked_book and target_submission.linked_book.deleted_at:
                target_submission.linked_book = None
                update_fields.append("linked_book")
            if target_submission.duplicate_of_book_id:
                target_submission.duplicate_of_book = None
                update_fields.append("duplicate_of_book")
            if target_submission.error_message:
                target_submission.error_message = ""
                update_fields.append("error_message")
            next_payload = dict(target_submission.raw_payload or {})
            payload_changed = False
            for key in ("served_from_database", "existing_book_source", "linked_book_slug"):
                if key in next_payload:
                    next_payload.pop(key, None)
                    payload_changed = True
            if payload_changed:
                target_submission.raw_payload = next_payload
                update_fields.append("raw_payload")

            can_queue_recreate = bool(target_submission.resolved_url or target_submission.input_type == "title")
            if can_queue_recreate:
                locked_response = automation_manual_creation_locked_response()
                if locked_response:
                    return locked_response
                target_submission.review_state = ReviewState.PENDING
                update_fields.append("review_state")
            else:
                target_submission.status = SubmissionStatus.NEEDS_REVIEW
                target_submission.review_state = ReviewState.NEEDS_REVIEW
                update_fields.extend(["status", "review_state"])

            if update_fields:
                target_submission.save(update_fields=[*dict.fromkeys(update_fields), "updated_at"])
            if can_queue_recreate:
                ingestion_views.queue_submission(target_submission, actor=request.user)
                review.submission.refresh_from_db()
            review.status = DuplicateReviewStatus.DISMISSED

        review.save(update_fields=["status", "notes", "updated_at"])
        return Response(DuplicateReviewSerializer(review, context={"request": request}).data)


__all__ = ["DuplicateReviewListView", "DuplicateReviewResolveView"]
