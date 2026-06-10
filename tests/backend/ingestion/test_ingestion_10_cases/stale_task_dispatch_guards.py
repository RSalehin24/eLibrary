

@pytest.mark.django_db
def test_source_catalog_refresh_ignores_stale_task_after_stop(monkeypatch):
    state = SourceCatalogRefreshState.objects.create(
        singleton_key="default",
        status=SourceCatalogRefreshStatus.IDLE,
        task_id="",
        queue_name="",
    )

    def fail_refresh_catalog(*_args, **_kwargs):
        raise AssertionError("stale source refresh task should not run")

    monkeypatch.setattr(
        "apps.ingestion.services.curation_support.source_refresh.TitleResolver.refresh_catalog",
        fail_refresh_catalog,
    )

    result = process_source_catalog_refresh(task_id="stale-task-id")

    state.refresh_from_db()
    assert result.id == state.id
    assert state.status == SourceCatalogRefreshStatus.IDLE


@pytest.mark.django_db
def test_source_catalog_refresh_ignores_completion_after_stop(monkeypatch):
    SourceCatalogRefreshState.objects.create(
        singleton_key="default",
        status=SourceCatalogRefreshStatus.QUEUED,
        task_id="active-task-id",
        queue_name="celery",
    )

    def fake_refresh_catalog(*_args, **_kwargs):
        state = SourceCatalogRefreshState.objects.get(singleton_key="default")
        state.status = SourceCatalogRefreshStatus.IDLE
        state.task_id = ""
        state.queue_name = ""
        state.last_error = "Stopped by user."
        state.finished_at = timezone.now()
        state.save(update_fields=["status", "task_id", "queue_name", "last_error", "finished_at", "updated_at"])
        return [{"source_url": "https://www.example.com/books/new-book/"}]

    monkeypatch.setattr(
        "apps.ingestion.services.curation_support.source_refresh.TitleResolver.refresh_catalog",
        fake_refresh_catalog,
    )

    result = process_source_catalog_refresh(task_id="active-task-id")

    state = SourceCatalogRefreshState.objects.get(singleton_key="default")
    assert result.id == state.id
    assert state.status == SourceCatalogRefreshStatus.IDLE
    assert state.task_id == ""
    assert state.last_error == "Stopped by user."
    assert state.refreshed_entries == 0


@pytest.mark.django_db
def test_source_catalog_refresh_ignores_completion_after_replacement(monkeypatch):
    SourceCatalogRefreshState.objects.create(
        singleton_key="default",
        status=SourceCatalogRefreshStatus.QUEUED,
        task_id="old-task-id",
        queue_name="celery",
    )

    def fake_refresh_catalog(*_args, **_kwargs):
        state = SourceCatalogRefreshState.objects.get(singleton_key="default")
        state.status = SourceCatalogRefreshStatus.QUEUED
        state.task_id = "new-task-id"
        state.queue_name = "celery"
        state.last_error = ""
        state.finished_at = None
        state.save(update_fields=["status", "task_id", "queue_name", "last_error", "finished_at", "updated_at"])
        return [{"source_url": "https://www.example.com/books/new-book/"}]

    monkeypatch.setattr(
        "apps.ingestion.services.curation_support.source_refresh.TitleResolver.refresh_catalog",
        fake_refresh_catalog,
    )

    result = process_source_catalog_refresh(task_id="old-task-id")

    state = SourceCatalogRefreshState.objects.get(singleton_key="default")
    assert result.id == state.id
    assert state.status == SourceCatalogRefreshStatus.QUEUED
    assert state.task_id == "new-task-id"
    assert state.queue_name == "celery"
    assert state.refreshed_entries == 0


@pytest.mark.django_db
def test_source_catalog_refresh_ignores_failure_after_replacement(monkeypatch):
    SourceCatalogRefreshState.objects.create(
        singleton_key="default",
        status=SourceCatalogRefreshStatus.QUEUED,
        task_id="old-task-id",
        queue_name="celery",
    )

    def fail_refresh_catalog(*_args, **_kwargs):
        state = SourceCatalogRefreshState.objects.get(singleton_key="default")
        state.status = SourceCatalogRefreshStatus.QUEUED
        state.task_id = "new-task-id"
        state.queue_name = "celery"
        state.last_error = ""
        state.finished_at = None
        state.save(update_fields=["status", "task_id", "queue_name", "last_error", "finished_at", "updated_at"])
        raise RuntimeError("old refresh failed after replacement")

    monkeypatch.setattr(
        "apps.ingestion.services.curation_support.source_refresh.TitleResolver.refresh_catalog",
        fail_refresh_catalog,
    )

    result = process_source_catalog_refresh(task_id="old-task-id")

    state = SourceCatalogRefreshState.objects.get(singleton_key="default")
    assert result.id == state.id
    assert state.status == SourceCatalogRefreshStatus.QUEUED
    assert state.task_id == "new-task-id"
    assert state.queue_name == "celery"
    assert state.last_error == ""


@pytest.mark.django_db
def test_dispatch_processing_job_returns_failed_job_after_eager_execution_error(monkeypatch, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    submission = BookSubmission.objects.create(
        input_type="url",
        original_input="https://www.example.com/books/eager-job/",
        normalized_input=normalize_text("https://www.example.com/books/eager-job/"),
        resolved_url="https://www.example.com/books/eager-job/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    job = ProcessingJob.objects.create(submission=submission, status=JobStatus.QUEUED)

    def fake_apply_async(args=None, task_id=None, **_kwargs):
        eager_job = ProcessingJob.objects.get(pk=args[0])
        eager_job.status = JobStatus.FAILED
        eager_job.task_id = task_id
        eager_job.queue_name = "celery"
        eager_job.last_error = "eager-job-failure"
        eager_job.finished_at = timezone.now()
        eager_job.save(update_fields=["status", "task_id", "queue_name", "last_error", "finished_at", "updated_at"])
        eager_job.submission.status = SubmissionStatus.FAILED
        eager_job.submission.error_message = "eager-job-failure"
        eager_job.submission.save(update_fields=["status", "error_message", "updated_at"])
        raise RuntimeError("eager-job-failure")

    monkeypatch.setattr("apps.ingestion.tasks.process_submission_task.apply_async", fake_apply_async)
    monkeypatch.setattr(
        "apps.ingestion.services.submissions.process_submission_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("inline fallback should not rerun eager job failures")),
    )

    result = dispatch_processing_job(job)

    job.refresh_from_db()
    submission.refresh_from_db()
    assert result.id == job.id
    assert job.status == JobStatus.FAILED
    assert job.queue_name == "celery"
    assert job.task_id
    assert submission.status == SubmissionStatus.FAILED


@pytest.mark.django_db
def test_dispatch_source_catalog_refresh_returns_failed_state_after_eager_execution_error(monkeypatch, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    state = SourceCatalogRefreshState.objects.create(
        singleton_key="default",
        status=SourceCatalogRefreshStatus.QUEUED,
        task_id="",
        queue_name="",
    )

    def fake_apply_async(*_args, task_id=None, **_kwargs):
        refresh_state = SourceCatalogRefreshState.objects.get(singleton_key="default")
        refresh_state.status = SourceCatalogRefreshStatus.FAILED
        refresh_state.task_id = task_id or refresh_state.task_id
        refresh_state.queue_name = "celery"
        refresh_state.last_error = "eager-refresh-failure"
        refresh_state.finished_at = timezone.now()
        refresh_state.save(update_fields=["status", "task_id", "queue_name", "last_error", "finished_at", "updated_at"])
        raise RuntimeError("eager-refresh-failure")

    monkeypatch.setattr("apps.ingestion.tasks.refresh_source_catalog_task.apply_async", fake_apply_async)
    monkeypatch.setattr(
        "apps.ingestion.services.curation.process_source_catalog_refresh",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("inline fallback should not rerun eager refresh failures")),
    )

    result = dispatch_source_catalog_refresh(state)

    state.refresh_from_db()
    assert result.id == state.id
    assert state.status == SourceCatalogRefreshStatus.FAILED
    assert state.queue_name == "celery"
    assert state.task_id


@pytest.mark.django_db
def test_dispatch_catalog_curation_run_returns_failed_run_after_eager_execution_error(monkeypatch, settings):
    settings.CELERY_TASK_ALWAYS_EAGER = True
    run = CatalogCurationRun.objects.create(status=JobStatus.QUEUED)

    def fake_apply_async(args=None, task_id=None, **_kwargs):
        eager_run = CatalogCurationRun.objects.get(pk=args[0])
        eager_run.status = JobStatus.FAILED
        eager_run.task_id = task_id or eager_run.task_id
        eager_run.queue_name = "celery"
        eager_run.last_error = "eager-run-failure"
        eager_run.finished_at = timezone.now()
        eager_run.save(update_fields=["status", "task_id", "queue_name", "last_error", "finished_at", "updated_at"])
        raise RuntimeError("eager-run-failure")

    monkeypatch.setattr("apps.ingestion.tasks.process_catalog_curation_run_task.apply_async", fake_apply_async)
    monkeypatch.setattr(
        "apps.ingestion.services.curation.process_catalog_curation_run",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("inline fallback should not rerun eager curation failures")),
    )

    result = dispatch_catalog_curation_run(run)

    run.refresh_from_db()
    assert result.id == run.id
    assert run.status == JobStatus.FAILED
    assert run.queue_name == "celery"
    assert run.task_id
