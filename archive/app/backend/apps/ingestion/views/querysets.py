from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from django.db.models.functions import Coalesce
from rest_framework.exceptions import PermissionDenied

from apps.ingestion.models import (
    BookSubmission,
    DuplicateReviewStatus,
    JobStatus,
    ProcessingJob,
    SubmissionStatus,
    TitleResolutionAttempt,
)
from apps.ingestion.services.submissions import can_manage_processing_records

from .filters import status_order_expression

HEAVY_BOOK_LIST_FIELDS = (
    "summary",
    "raw_scraped_metadata",
    "raw_scrape_payload",
    "main_content_html",
    "book_info_html",
    "dedication_html",
    "toc",
    "content_items",
)


def related_book_list_defer_fields(*prefixes):
    return [
        f"{prefix}{field}"
        for prefix in prefixes
        for field in HEAVY_BOOK_LIST_FIELDS
    ]


def resolution_attempt_list_prefetch():
    return Prefetch(
        "resolution_attempts",
        queryset=TitleResolutionAttempt.objects.defer(
            "raw_results",
            "error_message",
        ).prefetch_related("match_candidates"),
    )


def processing_job_list_prefetch(relation_name="processing_jobs"):
    return Prefetch(
        relation_name,
        queryset=ProcessingJob.objects.select_related("book").defer(
            "payload",
            *related_book_list_defer_fields("book__"),
        ),
    )


def submission_base_queryset():
    return BookSubmission.objects.select_related(
        "linked_book",
        "duplicate_of_book",
        "submitter",
        "canonical_submission",
        "canonical_submission__linked_book",
    ).defer(
        *related_book_list_defer_fields(
            "linked_book__",
            "duplicate_of_book__",
            "canonical_submission__linked_book__",
        ),
    ).prefetch_related(
        resolution_attempt_list_prefetch(),
        processing_job_list_prefetch(),
        Prefetch(
            "canonical_submission__resolution_attempts",
            queryset=TitleResolutionAttempt.objects.defer(
                "raw_results",
                "error_message",
            ).prefetch_related("match_candidates"),
        ),
        processing_job_list_prefetch("canonical_submission__processing_jobs"),
    )


def submissions_ordered_queryset(queryset):
    return queryset.order_by(
        status_order_expression(
            "status",
            [
                SubmissionStatus.PROCESSING,
                SubmissionStatus.PENDING_RESOLUTION,
                SubmissionStatus.QUEUED,
                SubmissionStatus.NEEDS_REVIEW,
                SubmissionStatus.FAILED,
                SubmissionStatus.DUPLICATE,
                SubmissionStatus.CANCELLED,
                SubmissionStatus.READY,
                SubmissionStatus.DELETED,
                SubmissionStatus.DRAFT,
            ],
        ),
        "-updated_at",
        "-created_at",
    )


def jobs_ordered_queryset(queryset):
    return queryset.annotate(activity_at=Coalesce("finished_at", "started_at", "updated_at", "created_at")).order_by(
        status_order_expression(
            "status",
            [
                JobStatus.PROCESSING,
                JobStatus.QUEUED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.SUCCEEDED,
            ],
        ),
        "-activity_at",
        "-created_at",
    )


def runs_ordered_queryset(queryset):
    return queryset.annotate(activity_at=Coalesce("finished_at", "started_at", "updated_at", "created_at")).order_by(
        status_order_expression(
            "status",
            [
                JobStatus.PROCESSING,
                JobStatus.QUEUED,
                JobStatus.FAILED,
                JobStatus.CANCELLED,
                JobStatus.SUCCEEDED,
            ],
        ),
        "-activity_at",
        "-created_at",
    )


def duplicate_reviews_ordered_queryset(queryset):
    return queryset.order_by(
        status_order_expression(
            "status",
            [
                DuplicateReviewStatus.PENDING,
                DuplicateReviewStatus.CONFIRMED,
                DuplicateReviewStatus.DISMISSED,
                DuplicateReviewStatus.MERGED,
            ],
        ),
        "-updated_at",
        "-created_at",
    )


def visible_submissions_queryset(user):
    queryset = submission_base_queryset()
    if can_manage_processing_records(user):
        return queryset
    return queryset.filter(submitter=user)


def visible_jobs_queryset(user):
    queryset = ProcessingJob.objects.select_related(
        "submission",
        "submission__linked_book",
        "book",
    ).defer(
        "payload",
        "submission__raw_payload",
        *related_book_list_defer_fields("submission__linked_book__", "book__"),
    )
    if can_manage_processing_records(user):
        return queryset
    return queryset.filter(submission__submitter=user)


def has_active_root_jobs(submission):
    target_submission = submission.canonical_submission or submission
    if target_submission.pk != submission.pk:
        return False
    return target_submission.processing_jobs.filter(status__in=[JobStatus.QUEUED, JobStatus.PROCESSING]).exists()


def is_public_submission(submission):
    return submission.submitter_id is None and bool(submission.raw_payload.get("submitted_publicly"))


def get_accessible_submission(request, pk):
    submission = get_object_or_404(submission_base_queryset(), pk=pk)
    user = request.user
    if getattr(user, "is_authenticated", False):
        if can_manage_processing_records(user):
            return submission
        if submission.submitter_id == user.id:
            return submission
    if is_public_submission(submission):
        return submission
    raise PermissionDenied("You do not have access to this submission.")


__all__ = [
    "duplicate_reviews_ordered_queryset",
    "get_accessible_submission",
    "has_active_root_jobs",
    "is_public_submission",
    "jobs_ordered_queryset",
    "processing_job_list_prefetch",
    "related_book_list_defer_fields",
    "resolution_attempt_list_prefetch",
    "runs_ordered_queryset",
    "submission_base_queryset",
    "submissions_ordered_queryset",
    "visible_jobs_queryset",
    "visible_submissions_queryset",
]
