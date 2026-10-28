def process_submission_job(job_id, retry_count=0, task_id=""):
    from .book_persistence import (
        cancel_requested_for_job,
        complete_processed_submission,
        persist_curated_book,
        sync_assets,
    )
    from .job_lifecycle import (
        CuratedDocumentStatus,
        JobStatus,
        JobType,
        ProcessingJob,
        SubmissionStatus,
        curate_book_document,
        curate_scraped_book_data,
        curated_document_with_projection,
        export_payload_from_book,
        finalize_cancelled_job,
        find_existing_book_by_source_url,
        generate_exports,
        high_fidelity_scrape_limits,
        normalize_source_url,
        persist_curated_document,
        record_job_log,
        scrape_book,
        scrape_book_high_fidelity,
        timezone,
    )
    from .resolution_and_queueing import (
        fulfill_submission_with_existing_book,
        resolve_submission,
    )
    from .retry_and_deduplication import (
        capture_source_page_metadata,
        sync_deduplicated_submissions,
    )

    job = ProcessingJob.objects.select_related(
        "submission", "submission__submitter", "book"
    ).get(pk=job_id)
    submission = job.submission
    reprocess_book = None
    if job.status == JobStatus.SUCCEEDED:
        return job
    if job.status == JobStatus.CANCELLED:
        return job
    if job.cancel_requested:
        return finalize_cancelled_job(job)
    job.status = JobStatus.PROCESSING
    job.retry_count = retry_count
    job.task_id = task_id or job.task_id
    job.started_at = timezone.now()
    job.save(
        update_fields=["status", "retry_count", "task_id", "started_at", "updated_at"]
    )

    submission.status = SubmissionStatus.PROCESSING
    submission.save(update_fields=["status", "updated_at"])
    sync_deduplicated_submissions(submission)
    record_job_log(
        job,
        "info",
        "Started processing submission.",
        {"submission_id": str(submission.id)},
    )

    try:
        if cancel_requested_for_job(job):
            return finalize_cancelled_job(job)
        if not submission.resolved_url and submission.input_type == "title":
            resolve_submission(submission, force_refresh=True)
            if not submission.resolved_url:
                job.status = JobStatus.FAILED
                job.finished_at = timezone.now()
                job.save(update_fields=["status", "finished_at", "updated_at"])
                record_job_log(
                    job,
                    "warning",
                    "The source title could not be resolved automatically.",
                )
                sync_deduplicated_submissions(submission)
                return job

        normalized_url = normalize_source_url(submission.resolved_url)
        if job.job_type == JobType.REPROCESS:
            from .reprocessing import prepare_regeneration

            reprocess_book = prepare_regeneration(job)

        if cancel_requested_for_job(job):
            return finalize_cancelled_job(job)
        source_page_metadata = capture_source_page_metadata(normalized_url)
        if source_page_metadata:
            submission.raw_payload = {
                **submission.raw_payload,
                "source_page_metadata": source_page_metadata["raw_data"],
            }
            submission.save(update_fields=["raw_payload", "updated_at"])
        source_duplicate = (
            None if reprocess_book else find_existing_book_by_source_url(normalized_url)
        )
        if source_duplicate:
            fulfill_submission_with_existing_book(
                submission,
                source_duplicate,
                source="processing_source_url",
                confidence=1.0,
                resolved_url=normalized_url,
            )
            record_job_log(
                job, "info", "Submission matched an existing book by exact source URL."
            )
            job.book = source_duplicate
            job.status = JobStatus.SUCCEEDED
            job.finished_at = timezone.now()
            job.save(update_fields=["book", "status", "finished_at", "updated_at"])
            return job

        if cancel_requested_for_job(job):
            return finalize_cancelled_job(job)
        legacy_scrape_overridden = (
            getattr(scrape_book, "__module__", "")
            != "apps.ingestion.services.legacy_adapter"
            or getattr(scrape_book_high_fidelity, "__module__", "")
            != "apps.ingestion.services.legacy_adapter"
        )
        if legacy_scrape_overridden:
            raw_scraped_data = (
                scrape_book_high_fidelity(submission.resolved_url)
                if reprocess_book is not None
                else scrape_book(submission.resolved_url)
            )
            curated_result = curate_scraped_book_data(normalized_url, raw_scraped_data)
        else:
            content_limits = (
                high_fidelity_scrape_limits() if reprocess_book is not None else None
            )
            curated_result = curate_book_document(
                normalized_url, content_limits=content_limits
            )
        scraped_data = curated_result.get("projection", {})
        if not isinstance(scraped_data, dict):
            raise TypeError(
                f"Source curation returned no content for {submission.resolved_url}. "
                "Verify the source URL is valid and publicly reachable."
            )
        record_job_log(
            job,
            "info",
            "Curated source content.",
            {
                "title": scraped_data.get("book_title", ""),
                "status": curated_result.get("status", ""),
                "structure_type": curated_result.get("document", {}).get(
                    "structure_type", ""
                ),
            },
        )
        if cancel_requested_for_job(job):
            return finalize_cancelled_job(job)
        if (
            not legacy_scrape_overridden
            and curated_result.get("status") == CuratedDocumentStatus.INVALID
            and not scraped_data.get("book_title")
        ):
            curated_document = persist_curated_document(curated_result, job=job)
            submission.status = SubmissionStatus.FAILED
            submission.error_message = (
                "Curated document failed automatic validation; no book was created."
            )
            submission.raw_payload = {
                **submission.raw_payload,
                "curated_document_id": str(curated_document.id),
                "curated_validation": curated_result.get("validation", {}),
            }
            submission.save(
                update_fields=["status", "error_message", "raw_payload", "updated_at"]
            )
            sync_deduplicated_submissions(submission)
            job.status = JobStatus.FAILED
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at", "updated_at"])
            record_job_log(
                job,
                "warning",
                "Curated document failed automatic validation; no files were generated.",
            )
            return job

        book, curated_document = persist_curated_book(
            submission,
            job,
            curated_result,
            target_book=reprocess_book,
        )
        if (
            not legacy_scrape_overridden
            and curated_result.get("status") != CuratedDocumentStatus.VALIDATED
        ):
            submission.linked_book = book
            submission.status = SubmissionStatus.FAILED
            submission.error_message = (
                "Curated document failed automatic validation before file generation."
            )
            submission.raw_payload = {
                **submission.raw_payload,
                "normalized_url": normalized_url,
                "linked_book_slug": book.slug,
                "curated_document_id": str(curated_document.id),
                "curated_validation": curated_result.get("validation", {}),
            }
            submission.save(
                update_fields=[
                    "linked_book",
                    "status",
                    "error_message",
                    "raw_payload",
                    "updated_at",
                ]
            )
            sync_deduplicated_submissions(submission)
            job.book = book
            job.status = JobStatus.FAILED
            job.finished_at = timezone.now()
            job.save(update_fields=["book", "status", "finished_at", "updated_at"])
            record_job_log(
                job,
                "warning",
                "Curated document failed automatic validation; no files were generated.",
            )
            return job

        export_payload = export_payload_from_book(book, scraped_data)
        generate_exports(
            curated_document_with_projection(curated_result["document"], export_payload)
        )
        sync_assets(book, job, export_payload)
        record_job_log(
            job, "info", "Generated HTML and EPUB exports from canonical book data."
        )
        complete_processed_submission(
            submission,
            book,
            normalized_url,
            source="reprocess" if reprocess_book else "scrape",
        )
        job.book = book
        job.status = JobStatus.SUCCEEDED
        job.finished_at = timezone.now()
        job.save(update_fields=["book", "status", "finished_at", "updated_at"])
        record_job_log(
            job,
            "info",
            "Submission finished successfully.",
            {"book_id": str(book.id), "job_type": job.job_type},
        )
        return job
    except Exception as exc:
        from .job_failures import handle_submission_failure

        handle_submission_failure(job, exc, reprocess_book)
        raise


def legacy_config_entries_as_submission_inputs():
    from .job_lifecycle import load_legacy_config_entries

    return [
        {"kind": "url", "value": url, "label": name}
        for name, url in load_legacy_config_entries()
    ]


__all__ = ["legacy_config_entries_as_submission_inputs", "process_submission_job"]
