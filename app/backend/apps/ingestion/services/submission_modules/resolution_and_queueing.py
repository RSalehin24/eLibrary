from .job_dispatch import dispatch_processing_job as dispatch_processing_job
from .job_lifecycle import ResolutionStatus, SubmissionOrigin


def find_reusable_submission(*, normalized_input="", resolved_url="", exclude_submission_id=None):
    from .job_lifecycle import REUSABLE_SUBMISSION_STATUSES, BookSubmission, Q
    queryset = BookSubmission.objects.select_related(
        "linked_book",
        "duplicate_of_book",
        "submitter",
    ).filter(
        canonical_submission__isnull=True,
        status__in=REUSABLE_SUBMISSION_STATUSES,
    ).filter(
        Q(linked_book__isnull=True) | Q(linked_book__deleted_at__isnull=True),
        Q(duplicate_of_book__isnull=True) | Q(duplicate_of_book__deleted_at__isnull=True),
    )
    if exclude_submission_id:
        queryset = queryset.exclude(pk=exclude_submission_id)

    if resolved_url:
        submission = queryset.filter(resolved_url=resolved_url).order_by("-created_at").first()
        if submission:
            return submission

    if normalized_input:
        submission = queryset.filter(normalized_input=normalized_input).order_by("-created_at").first()
        if submission:
            return submission

    return None


def create_local_resolution_attempt(submission, book, confidence=1.0):
    from .job_lifecycle import (
        ResolutionStatus,
        TitleResolutionAttempt,
        primary_source_url_for_book,
    )
    return TitleResolutionAttempt.objects.create(
        submission=submission,
        query=submission.original_input,
        normalized_query=submission.normalized_input,
        status=ResolutionStatus.RESOLVED,
        confidence=confidence,
        resolved_url=primary_source_url_for_book(book),
        raw_results={
            "source": "local_database",
            "book_id": str(book.id),
            "book_slug": book.slug,
        },
    )


def fulfill_submission_with_existing_book(
    submission,
    book,
    source,
    confidence=1.0,
    resolution_status=ResolutionStatus.RESOLVED,
    resolved_url="",
):
    from .job_lifecycle import (
        AuditLog,
        SubmissionStatus,
        ensure_preview_session,
        primary_source_url_for_book,
    )
    from .retry_and_deduplication import sync_deduplicated_submissions
    if not resolved_url:
        resolved_url = primary_source_url_for_book(book)

    submission.linked_book = book
    submission.resolved_url = resolved_url
    submission.resolution_status = resolution_status
    submission.resolution_confidence = confidence
    submission.status = SubmissionStatus.READY
    submission.review_state = book.review_state
    submission.error_message = ""
    submission.raw_payload = {
        **submission.raw_payload,
        "served_from_database": True,
        "existing_book_source": source,
        "linked_book_slug": book.slug,
    }
    submission.save(update_fields=["linked_book", "resolved_url", "resolution_status", "resolution_confidence", "status", "review_state", "error_message", "raw_payload", "updated_at"])
    sync_deduplicated_submissions(submission)

    ensure_preview_session(submission.submitter, book, submission=submission)
    AuditLog.objects.create(
        actor=submission.submitter,
        verb="submission.fulfilled_from_database",
        target_type="BookSubmission",
        target_id=str(submission.id),
        payload={"book_id": str(book.id), "source": source},
    )
    return submission


def resolve_submission(submission, force_refresh=False):
    from .job_lifecycle import (
        MatchCandidate,
        ResolutionStatus,
        ReviewState,
        SubmissionStatus,
        TitleResolutionAttempt,
        TitleResolver,
    )
    from .retry_and_deduplication import sync_deduplicated_submissions
    resolver = TitleResolver()
    result = resolver.resolve(submission.original_input, refresh_catalog=force_refresh)
    attempt = TitleResolutionAttempt.objects.create(
        submission=submission,
        query=submission.original_input,
        normalized_query=submission.normalized_input,
        status=result.status,
        confidence=result.confidence,
        resolved_url=result.resolved_url,
        raw_results=result.raw,
    )

    for index, candidate in enumerate(result.candidates, start=1):
        MatchCandidate.objects.create(
            resolution_attempt=attempt,
            rank=index,
            candidate_title=candidate["title"],
            candidate_author=candidate.get("author", ""),
            candidate_url=candidate["url"],
            confidence=candidate["confidence"],
            metadata={"title": candidate["title"], "author": candidate.get("author", "")},
        )

    if result.status == "exact_match":
        submission.resolved_url = result.resolved_url
        submission.resolution_status = ResolutionStatus.EXACT_MATCH
        submission.resolution_confidence = result.confidence
        submission.status = SubmissionStatus.QUEUED
    elif result.status == "ambiguous":
        submission.resolution_status = ResolutionStatus.AMBIGUOUS
        submission.resolution_confidence = result.confidence
        submission.status = SubmissionStatus.NEEDS_REVIEW
        submission.review_state = ReviewState.NEEDS_REVIEW
    else:
        submission.resolution_status = ResolutionStatus.UNRESOLVED
        submission.status = SubmissionStatus.NEEDS_REVIEW
        submission.review_state = ReviewState.NEEDS_REVIEW
        submission.error_message = "No confident catalog match was found."

    submission.save(update_fields=["resolved_url", "resolution_status", "resolution_confidence", "status", "review_state", "error_message", "updated_at"])
    sync_deduplicated_submissions(submission)
    return submission


def queue_submission(submission, actor=None):
    from .job_lifecycle import (
        ACTIVE_JOB_STATUSES,
        JobStatus,
        JobType,
        ProcessingJob,
        SubmissionStatus,
        root_submission,
    )
    from .retry_and_deduplication import sync_deduplicated_submissions
    submission = root_submission(submission)
    existing_job = submission.processing_jobs.filter(status__in=ACTIVE_JOB_STATUSES).first()
    if existing_job:
        return existing_job

    job = ProcessingJob.objects.create(
        submission=submission,
        job_type=JobType.INGESTION,
        status=JobStatus.QUEUED,
        payload={
            "resolved_url": submission.resolved_url,
            "actor_id": getattr(actor, "id", None),
        },
    )
    submission.status = SubmissionStatus.QUEUED
    submission.save(update_fields=["status", "updated_at"])
    sync_deduplicated_submissions(submission)

    dispatch_processing_job(job)
    return job




def queue_reprocess_book(book, actor=None, origin=SubmissionOrigin.USER):
    from .job_lifecycle import (
        ACTIVE_JOB_STATUSES,
        BookSubmission,
        JobStatus,
        JobType,
        LifecycleState,
        ProcessingJob,
        ResolutionStatus,
        SubmissionInputType,
        SubmissionStatus,
        normalize_source_url,
        normalize_text,
        primary_source_url_for_book,
    )
    existing_job = book.processing_jobs.filter(status__in=ACTIVE_JOB_STATUSES).first()
    if existing_job:
        return existing_job, False

    resolved_url = normalize_source_url(primary_source_url_for_book(book))
    submission = BookSubmission.objects.create(
        submitter=actor if getattr(actor, "is_authenticated", False) else None,
        input_type=SubmissionInputType.URL,
        origin=origin,
        original_input=resolved_url,
        normalized_input=normalize_text(resolved_url),
        resolved_url=resolved_url,
        resolution_status=ResolutionStatus.RESOLVED,
        resolution_confidence=1.0,
        status=SubmissionStatus.QUEUED,
        review_state=book.review_state,
        linked_book=book,
        raw_payload={
            "submitted_publicly": False,
            "reprocess_book_id": str(book.id),
        },
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        book=book,
        job_type=JobType.REPROCESS,
        status=JobStatus.QUEUED,
        payload={
            "resolved_url": resolved_url,
            "actor_id": getattr(actor, "id", None),
            "reprocess_book_id": str(book.id),
            "previous_book_state": book.state,
        },
    )
    book.state = LifecycleState.PROCESSING
    book.save(update_fields=["state", "updated_at"])

    dispatch_processing_job(job)
    return job, True


__all__ = ['create_local_resolution_attempt', 'dispatch_processing_job', 'find_reusable_submission', 'fulfill_submission_with_existing_book', 'queue_reprocess_book', 'queue_submission', 'resolve_submission']
