

@pytest.mark.django_db
def test_recover_stale_processing_jobs_requeues_stale_processing_work(monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/stale-processing/",
        normalized_input=normalize_text("https://www.example.com/books/stale-processing/"),
        resolved_url="https://www.example.com/books/stale-processing/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.PROCESSING,
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.PROCESSING,
        retry_count=0,
        task_id="stale-task-id",
        queue_name="celery",
        started_at=timezone.now() - timedelta(minutes=45),
    )
    revoked = []
    dispatched = []

    monkeypatch.setattr(
        "apps.ingestion.services.submissions.revoke_processing_task",
        lambda task_id, terminate=False: revoked.append((task_id, terminate)),
    )

    def fake_apply_async(args=None, kwargs=None, task_id=None, **_extra_kwargs):
        dispatched.append(
            {
                "args": args,
                "kwargs": kwargs,
                "task_id": task_id,
            }
        )
        return type("AsyncResult", (), {"id": task_id})()

    monkeypatch.setattr(
        "apps.ingestion.tasks.process_submission_task.apply_async",
        fake_apply_async,
    )

    recovered = recover_stale_processing_jobs(limit=10)

    job.refresh_from_db()
    submission.refresh_from_db()
    assert recovered == 1
    assert revoked == [("stale-task-id", True)]
    assert dispatched == [
        {
            "args": [str(job.id)],
            "kwargs": {"attempt_offset": 1},
            "task_id": job.task_id,
        }
    ]
    assert job.status == JobStatus.QUEUED
    assert job.retry_count == 1
    assert job.queue_name == "celery"
    assert job.task_id
    assert job.last_error
    assert submission.status == SubmissionStatus.QUEUED
    assert submission.error_message == ""


@pytest.mark.django_db
def test_recover_stale_processing_jobs_fails_exhausted_processing_work(monkeypatch):
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/stale-processing-final/",
        normalized_input=normalize_text("https://www.example.com/books/stale-processing-final/"),
        resolved_url="https://www.example.com/books/stale-processing-final/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.PROCESSING,
    )
    job = ProcessingJob.objects.create(
        submission=submission,
        status=JobStatus.PROCESSING,
        retry_count=MAX_PROCESSING_JOB_ATTEMPTS - 1,
        task_id="stale-final-task-id",
        queue_name="celery",
        started_at=timezone.now() - timedelta(minutes=45),
    )
    revoked = []

    monkeypatch.setattr(
        "apps.ingestion.services.submissions.revoke_processing_task",
        lambda task_id, terminate=False: revoked.append((task_id, terminate)),
    )
    monkeypatch.setattr(
        "apps.ingestion.tasks.process_submission_task.apply_async",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("exhausted stale jobs must not be re-dispatched")
        ),
    )

    recovered = recover_stale_processing_jobs(limit=10)

    job.refresh_from_db()
    submission.refresh_from_db()
    assert recovered == 0
    assert revoked == [("stale-final-task-id", True)]
    assert job.status == JobStatus.FAILED
    assert job.task_id == ""
    assert job.queue_name == ""
    assert submission.status == SubmissionStatus.FAILED
    assert submission.error_message == job.last_error
