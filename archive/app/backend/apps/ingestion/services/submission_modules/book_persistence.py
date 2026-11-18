

def create_submission_records(submitter, parsed_entries, auto_process=True, origin=SubmissionOrigin.USER):
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
                source_metadata = capture_source_page_metadata(submission.resolved_url)
                if source_metadata:
                    submission.raw_payload = {
                        **submission.raw_payload,
                        "source_page_metadata": source_metadata["raw_data"],
                    }
                existing_book = find_existing_book_by_source_url(submission.resolved_url)
                if existing_book:
                    fulfill_submission_with_existing_book(
                        submission,
                        existing_book,
                        source="source_url",
                        confidence=1.0,
                    )
                    submissions.append(submission)
                    continue
                submission.resolution_status = ResolutionStatus.RESOLVED
                submission.resolution_confidence = 1.0
                submission.status = SubmissionStatus.QUEUED
                submission.save(update_fields=["resolved_url", "raw_payload", "resolution_status", "resolution_confidence", "status", "updated_at"])
            except ValueError as exc:
                submission.resolution_status = ResolutionStatus.INVALID
                submission.status = SubmissionStatus.NEEDS_REVIEW
                submission.review_state = ReviewState.NEEDS_REVIEW
                submission.error_message = str(exc)
                submission.save(update_fields=["resolution_status", "status", "review_state", "error_message", "updated_at"])
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
                existing_book = find_existing_book_by_source_url(submission.resolved_url)
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

        if auto_process and submission.resolved_url and submission.status == SubmissionStatus.QUEUED:
            queue_submission(submission, actor=submitter)
            submission.refresh_from_db()

        submissions.append(submission)

    return submissions


def detect_metadata_duplicate(scraped_data):
    return _detect_metadata_duplicate(
        scraped_data,
        normalize_scraped_book_fn=normalize_scraped_book,
        texts_are_similar_fn=texts_are_similar,
    )


def find_exact_existing_book(scraped_data):
    return _find_exact_existing_book(
        scraped_data,
        normalize_scraped_book_fn=normalize_scraped_book,
    )


def sync_assets(book, job, scraped_data):
    return _sync_assets(
        book,
        job,
        scraped_data,
        generated_asset_labels=GENERATED_ASSET_LABELS,
        required_asset_types=REQUIRED_GENERATED_ASSET_TYPES,
    )


def complete_processed_submission(submission, book, normalized_url, source="scrape"):
    return _complete_processed_submission(
        submission,
        book,
        normalized_url,
        ensure_preview_session_fn=ensure_preview_session,
        source=source,
        sync_deduplicated_submissions_fn=sync_deduplicated_submissions,
    )


def sync_metadata_relations(book, normalized):
    return _sync_metadata_relations(
        book,
        normalized,
        replace_book_relations_fn=replace_book_relations,
    )


def persist_scraped_book(submission, job, scraped_data, target_book=None):
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
    job.refresh_from_db(fields=["status", "cancel_requested", "updated_at"])
    return job.status == JobStatus.CANCELLED or job.cancel_requested
