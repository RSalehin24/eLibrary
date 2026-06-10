

def test_normalize_scraped_book_drops_author_role_when_same_person_is_translator_or_editor():
    normalized = normalize_scraped_book(
        {
            "book_title": "উদাহরণ",
            "author": "ইশরাক অর্ণব, কেইগো হিগাশিনো, সালমান হক",
            "series": "",
            "book_type": "",
            "book_info": """
            <p><strong>অনুবাদ</strong>: ইশরাক অর্ণব</p>
            <p><strong>সম্পাদক</strong>: কেইগো হিগাশিনো</p>
            """,
        }
    )

    contributor_roles = {(entry["name"], entry["role"]) for entry in normalized["contributors"]}

    assert ("সালমান হক", "author") in contributor_roles
    assert ("ইশরাক অর্ণব", "translator") in contributor_roles
    assert ("কেইগো হিগাশিনো", "editor") in contributor_roles
    assert ("ইশরাক অর্ণব", "author") not in contributor_roles
    assert ("কেইগো হিগাশিনো", "author") not in contributor_roles


@pytest.mark.django_db
def test_queue_submission_falls_back_to_inline_processing_when_celery_dispatch_fails(monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/fallback/",
        normalized_input=normalize_text("https://www.example.com/books/fallback/"),
        resolved_url="https://www.example.com/books/fallback/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )

    def fail_apply_async(args=None, task_id=None, **_kwargs):
        raise RuntimeError("Error 111 connecting to redis")

    def fake_process(job_id, retry_count=0, task_id=""):
        job = ProcessingJob.objects.get(pk=job_id)
        job.status = JobStatus.SUCCEEDED
        job.save(update_fields=["status", "updated_at"])
        job.submission.status = SubmissionStatus.READY
        job.submission.save(update_fields=["status", "updated_at"])
        return job

    monkeypatch.setattr("apps.ingestion.tasks.process_submission_task.apply_async", fail_apply_async)
    monkeypatch.setattr("apps.ingestion.services.submissions.process_submission_job", fake_process)

    job = queue_submission(submission)

    assert job.queue_name == "inline-fallback"
    assert "Celery dispatch failed" in job.last_error
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.READY


@pytest.mark.django_db
def test_queue_submission_inline_fallback_retries_up_to_three_total_attempts(monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/fallback-retry/",
        normalized_input=normalize_text("https://www.example.com/books/fallback-retry/"),
        resolved_url="https://www.example.com/books/fallback-retry/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    attempts = []

    def fail_apply_async(args=None, task_id=None, **_kwargs):
        raise RuntimeError("Error 111 connecting to redis")

    def fake_process(job_id, retry_count=0, task_id=""):
        attempts.append(retry_count)
        job = ProcessingJob.objects.get(pk=job_id)
        job.retry_count = retry_count
        if retry_count < MAX_PROCESSING_JOB_ATTEMPTS - 1:
            job.status = JobStatus.FAILED
            job.last_error = f"retry-{retry_count}"
            job.save(update_fields=["retry_count", "status", "last_error", "updated_at"])
            raise RuntimeError(f"retry-{retry_count}")

        job.status = JobStatus.SUCCEEDED
        job.save(update_fields=["retry_count", "status", "updated_at"])
        job.submission.status = SubmissionStatus.READY
        job.submission.save(update_fields=["status", "updated_at"])
        return job

    monkeypatch.setattr("apps.ingestion.tasks.process_submission_task.apply_async", fail_apply_async)
    monkeypatch.setattr("apps.ingestion.services.submissions.process_submission_job", fake_process)

    job = queue_submission(submission)

    assert attempts == [0, 1, 2]
    assert job.queue_name == "inline-fallback"
    submission.refresh_from_db()
    assert submission.status == SubmissionStatus.READY


@pytest.mark.django_db
def test_queue_submission_inline_fallback_stops_after_three_total_attempts(monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/fallback-stop/",
        normalized_input=normalize_text("https://www.example.com/books/fallback-stop/"),
        resolved_url="https://www.example.com/books/fallback-stop/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    attempts = []

    def fail_apply_async(args=None, task_id=None, **_kwargs):
        raise RuntimeError("Error 111 connecting to redis")

    def fake_process(job_id, retry_count=0, task_id=""):
        attempts.append(retry_count)
        job = ProcessingJob.objects.get(pk=job_id)
        job.retry_count = retry_count
        job.status = JobStatus.FAILED
        job.last_error = f"retry-{retry_count}"
        job.save(update_fields=["retry_count", "status", "last_error", "updated_at"])
        raise RuntimeError(f"retry-{retry_count}")

    monkeypatch.setattr("apps.ingestion.tasks.process_submission_task.apply_async", fail_apply_async)
    monkeypatch.setattr("apps.ingestion.services.submissions.process_submission_job", fake_process)

    with pytest.raises(RuntimeError, match="retry-2"):
        queue_submission(submission)

    assert attempts == [0, 1, 2]
    job = ProcessingJob.objects.get(submission=submission)
    assert job.retry_count == 2
    assert job.status == JobStatus.FAILED


@pytest.mark.django_db
def test_process_submission_task_returns_serializable_job_payload(monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/2001-space-odyssey/",
        normalized_input=normalize_text("https://www.example.com/books/2001-space-odyssey/"),
        resolved_url="https://www.example.com/books/2001-space-odyssey/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(submission=submission, status=JobStatus.SUCCEEDED)

    monkeypatch.setattr("apps.ingestion.tasks.process_submission_job", lambda *args, **kwargs: job)

    result = process_submission_task.apply(args=[str(job.id)])

    assert result.result == {
        "job_id": str(job.id),
        "submission_id": str(submission.id),
        "book_id": "",
        "status": JobStatus.SUCCEEDED,
    }
    json.dumps(result.result)


@pytest.mark.django_db
def test_process_submission_task_uses_three_total_attempts():
    assert process_submission_task.max_retries == 2


@pytest.mark.django_db
def test_process_submission_job_requeues_intermediate_failures_without_becoming_terminal(monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/retry-intermediate/",
        normalized_input=normalize_text("https://www.example.com/books/retry-intermediate/"),
        resolved_url="https://www.example.com/books/retry-intermediate/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.QUEUED,
        task_id="celery-retry-task",
        queue_name="celery",
    )

    monkeypatch.setattr(
        "apps.ingestion.services.submissions.capture_source_page_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.scrape_book",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("temporary scrape failure")),
    )

    with pytest.raises(RuntimeError, match="temporary scrape failure"):
        process_submission_job(
            str(job.id),
            retry_count=1,
            task_id="celery-retry-task",
        )

    job.refresh_from_db()
    submission.refresh_from_db()
    assert job.status == JobStatus.QUEUED
    assert job.retry_count == 2
    assert job.task_id == "celery-retry-task"
    assert job.queue_name == "celery"
    assert "attempt 2 of 3" in job.last_error
    assert submission.status == SubmissionStatus.QUEUED
    assert submission.error_message == ""


@pytest.mark.django_db
def test_process_submission_job_marks_last_attempt_as_failed(monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/retry-final/",
        normalized_input=normalize_text("https://www.example.com/books/retry-final/"),
        resolved_url="https://www.example.com/books/retry-final/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.QUEUED,
        task_id="celery-final-task",
        queue_name="celery",
    )

    monkeypatch.setattr(
        "apps.ingestion.services.submissions.capture_source_page_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.scrape_book",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("permanent scrape failure")),
    )

    with pytest.raises(RuntimeError, match="permanent scrape failure"):
        process_submission_job(
            str(job.id),
            retry_count=MAX_PROCESSING_JOB_ATTEMPTS - 1,
            task_id="celery-final-task",
        )

    job.refresh_from_db()
    submission.refresh_from_db()
    assert job.status == JobStatus.FAILED
    assert job.retry_count == MAX_PROCESSING_JOB_ATTEMPTS - 1
    assert job.task_id == ""
    assert job.queue_name == ""
    assert submission.status == SubmissionStatus.FAILED
    assert submission.error_message == "permanent scrape failure"
