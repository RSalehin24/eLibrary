from .job_lifecycle import SubmissionOrigin


def create_submission_records(
    submitter, parsed_entries, auto_process=True, origin=SubmissionOrigin.USER
):
    from .job_lifecycle import (
        AuditLog,
        BookSubmission,
        ResolutionStatus,
        SubmissionStatus,
        find_existing_book_by_source_url,
        normalize_text,
        validate_source_url,
    )
    from .resolution_and_queueing import (
        find_reusable_submission,
        fulfill_submission_with_existing_book,
        queue_submission,
        resolve_submission,
    )
    from .retry_and_deduplication import (
        capture_source_page_metadata,
        sync_submission_from_canonical,
    )

    submissions = []

    for entry in parsed_entries:
        submission = BookSubmission.objects.create(
            submitter=submitter,
            input_type=entry["kind"],
            origin=origin,
            original_input=entry["value"],
            normalized_input=normalize_text(entry["value"]),
            status=SubmissionStatus.PENDING_RESOLUTION
            if entry["kind"] == "title"
            else SubmissionStatus.QUEUED,
            raw_payload={"submitted_publicly": submitter is None},
        )

        AuditLog.objects.create(
            actor=submitter,
            verb="submission.created",
            target_type="BookSubmission",
            target_id=str(submission.id),
            payload={"input_type": submission.input_type},
        )

        if entry["kind"] == "url":
            try:
                submission.resolved_url = validate_source_url(entry["value"])
                reusable_submission = find_reusable_submission(
                    resolved_url=submission.resolved_url,
                    exclude_submission_id=submission.id,
                )
                if reusable_submission:
                    sync_submission_from_canonical(submission, reusable_submission)
                    submissions.append(submission)
                    continue
                existing_book = find_existing_book_by_source_url(
                    submission.resolved_url
                )
                if existing_book:
                    fulfill_submission_with_existing_book(
                        submission,
                        existing_book,
                        source="source_url",
                        confidence=1.0,
                    )
                    submissions.append(submission)
                    continue
                source_metadata = capture_source_page_metadata(submission.resolved_url)
                if source_metadata:
                    submission.raw_payload = {
                        **submission.raw_payload,
                        "source_page_metadata": source_metadata["raw_data"],
                    }
                submission.resolution_status = ResolutionStatus.RESOLVED
                submission.resolution_confidence = 1.0
                submission.status = SubmissionStatus.QUEUED
                submission.save(
                    update_fields=[
                        "resolved_url",
                        "raw_payload",
                        "resolution_status",
                        "resolution_confidence",
                        "status",
                        "updated_at",
                    ]
                )
            except ValueError as exc:
                submission.resolution_status = ResolutionStatus.INVALID
                submission.status = SubmissionStatus.FAILED
                submission.error_message = str(exc)
                submission.save(
                    update_fields=[
                        "resolution_status",
                        "status",
                        "error_message",
                        "updated_at",
                    ]
                )
        else:
            reusable_submission = find_reusable_submission(
                normalized_input=submission.normalized_input,
                exclude_submission_id=submission.id,
            )
            if reusable_submission:
                sync_submission_from_canonical(submission, reusable_submission)
                submissions.append(submission)
                continue

            resolve_submission(submission)
            if submission.resolved_url:
                reusable_submission = find_reusable_submission(
                    resolved_url=submission.resolved_url,
                    exclude_submission_id=submission.id,
                )
                if reusable_submission:
                    sync_submission_from_canonical(submission, reusable_submission)
                    submissions.append(submission)
                    continue
                existing_book = find_existing_book_by_source_url(
                    submission.resolved_url
                )
                if existing_book:
                    fulfill_submission_with_existing_book(
                        submission,
                        existing_book,
                        source="resolved_source_url",
                        confidence=submission.resolution_confidence,
                        resolution_status=submission.resolution_status,
                        resolved_url=submission.resolved_url,
                    )
                    submissions.append(submission)
                    continue

        if (
            auto_process
            and submission.resolved_url
            and submission.status == SubmissionStatus.QUEUED
        ):
            queue_submission(submission, actor=submitter)
            submission.refresh_from_db()

        submissions.append(submission)

    return submissions


def detect_metadata_duplicate(scraped_data):
    from .job_lifecycle import (
        _detect_metadata_duplicate,
        normalize_scraped_book,
        texts_are_similar,
    )

    return _detect_metadata_duplicate(
        scraped_data,
        normalize_scraped_book_fn=normalize_scraped_book,
        texts_are_similar_fn=texts_are_similar,
    )


def find_exact_existing_book(scraped_data):
    from .job_lifecycle import _find_exact_existing_book, normalize_scraped_book

    return _find_exact_existing_book(
        scraped_data,
        normalize_scraped_book_fn=normalize_scraped_book,
    )


def sync_assets(book, job, scraped_data):
    from .job_lifecycle import (
        GENERATED_ASSET_LABELS,
        REQUIRED_GENERATED_ASSET_TYPES,
        _sync_assets,
    )

    return _sync_assets(
        book,
        job,
        scraped_data,
        generated_asset_labels=GENERATED_ASSET_LABELS,
        required_asset_types=REQUIRED_GENERATED_ASSET_TYPES,
    )


def complete_processed_submission(submission, book, normalized_url, source="scrape"):
    from .job_lifecycle import _complete_processed_submission, ensure_preview_session
    from .retry_and_deduplication import sync_deduplicated_submissions

    return _complete_processed_submission(
        submission,
        book,
        normalized_url,
        ensure_preview_session_fn=ensure_preview_session,
        source=source,
        sync_deduplicated_submissions_fn=sync_deduplicated_submissions,
    )


def sync_metadata_relations(book, normalized):
    from .job_lifecycle import _sync_metadata_relations, replace_book_relations

    return _sync_metadata_relations(
        book,
        normalized,
        replace_book_relations_fn=replace_book_relations,
    )


def persist_scraped_book(submission, job, scraped_data, target_book=None):
    from .job_lifecycle import (
        _persist_scraped_book,
        clean_extracted_dedication_html,
        find_deleted_book_by_title,
        find_existing_book_by_source_url,
        normalize_scraped_book,
        normalize_source_url,
    )

    return _persist_scraped_book(
        submission,
        scraped_data,
        clean_extracted_dedication_html_fn=clean_extracted_dedication_html,
        find_deleted_book_by_title_fn=find_deleted_book_by_title,
        find_existing_book_by_source_url_fn=find_existing_book_by_source_url,
        job=job,
        normalize_scraped_book_fn=normalize_scraped_book,
        normalize_source_url_fn=normalize_source_url,
        sync_metadata_relations_fn=sync_metadata_relations,
        target_book=target_book,
    )


def persist_curated_book(submission, job, curated_result, target_book=None):
    from .job_lifecycle import (
        _persist_curated_book,
        find_deleted_book_by_title,
        find_existing_book_by_source_url,
        replace_book_relations,
    )

    return _persist_curated_book(
        curated_result,
        source_url=submission.resolved_url,
        job=job,
        target_book=target_book,
        find_deleted_book_by_title_fn=find_deleted_book_by_title,
        find_existing_book_by_source_url_fn=find_existing_book_by_source_url,
        replace_book_relations_fn=replace_book_relations,
    )


def cancel_requested_for_job(job):
    from .job_lifecycle import JobStatus

    job.refresh_from_db(fields=["status", "cancel_requested", "updated_at"])
    return job.status == JobStatus.CANCELLED or job.cancel_requested


__all__ = [
    "cancel_requested_for_job",
    "complete_processed_submission",
    "create_submission_records",
    "detect_metadata_duplicate",
    "find_exact_existing_book",
    "persist_curated_book",
    "persist_scraped_book",
    "sync_assets",
    "sync_metadata_relations",
]
