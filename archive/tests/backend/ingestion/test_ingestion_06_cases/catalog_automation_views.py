

@pytest.mark.django_db
def test_processing_manager_can_start_catalog_curation_run(client, monkeypatch):
    admin = User.objects.create_superuser(email="curation-admin@example.com", password="strong-password-123")
    queued_run = CatalogCurationRun.objects.create(
        trigger="manual",
        mode="pending",
        status="queued",
        refresh_catalog=True,
        refresh_max_pages=80,
        requested_by=admin,
    )
    client.force_login(admin)

    monkeypatch.setattr("apps.ingestion.views.create_catalog_curation_run", lambda **kwargs: queued_run)

    response = client.post(
        "/api/ingestion/catalog/curation-runs/",
        data=json.dumps({"mode": "pending", "refresh_catalog": True, "refresh_max_pages": 80}),
        content_type="application/json",
    )

    assert response.status_code == 202
    assert response.json()["id"] == str(queued_run.id)
    assert response.json()["status"] == "queued"


@pytest.mark.django_db
def test_processing_manager_can_update_catalog_automation_settings(client):
    admin = User.objects.create_superuser(email="automation-admin@example.com", password="strong-password-123")
    client.force_login(admin)

    response = client.patch(
        "/api/ingestion/catalog/automation/",
        data=json.dumps(
            {
                "enabled": True,
                "daily_run_time": "03:45",
                "frequency": "weekly",
                "mode": "all",
                "refresh_max_pages": 40,
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    payload = response.json()["settings"]
    assert payload["enabled"] is True
    assert payload["daily_run_time"].startswith("03:45")
    assert payload["frequency"] == "weekly"
    assert payload["mode"] == "all"
    assert payload["refresh_max_pages"] == 40


@pytest.mark.django_db
def test_processing_lists_filter_by_origin_and_recover_stale_jobs(client, monkeypatch):
    admin = User.objects.create_superuser(email="origin-admin@example.com", password="strong-password-123")
    client.force_login(admin)

    user_submission = BookSubmission.objects.create(
        input_type="url",
        origin=SubmissionOrigin.USER,
        original_input="https://www.example.com/books/user-book/",
        normalized_input=normalize_text("https://www.example.com/books/user-book/"),
        resolved_url="https://www.example.com/books/user-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    curation_submission = BookSubmission.objects.create(
        input_type="url",
        origin=SubmissionOrigin.CURATION,
        original_input="https://www.example.com/books/source-book/",
        normalized_input=normalize_text("https://www.example.com/books/source-book/"),
        resolved_url="https://www.example.com/books/source-book/",
        resolution_status=ResolutionStatus.RESOLVED,
        status=SubmissionStatus.QUEUED,
    )
    user_job = ProcessingJob.objects.create(submission=user_submission, status=JobStatus.QUEUED)
    ProcessingJob.objects.create(submission=curation_submission, status=JobStatus.QUEUED, task_id="already-dispatched")
    dispatched_ids = []

    def fake_dispatch(job, force=False):
        dispatched_ids.append(str(job.id))
        job.task_id = f"task-{job.id}"
        job.queue_name = "celery"
        job.save(update_fields=["task_id", "queue_name", "updated_at"])
        return job

    monkeypatch.setattr("apps.ingestion.services.submissions.dispatch_processing_job", fake_dispatch)

    job_response = client.get("/api/ingestion/jobs/?origin=user")
    submission_response = client.get("/api/ingestion/submissions/?origin=curation")
    recover_response = client.post(
        "/api/ingestion/jobs/recover/",
        data=json.dumps({"origin": "user"}),
        content_type="application/json",
    )

    assert job_response.status_code == 200
    assert [entry["id"] for entry in job_response.json()] == [str(user_job.id)]
    assert submission_response.status_code == 200
    assert [entry["id"] for entry in submission_response.json()] == [str(curation_submission.id)]
    assert recover_response.status_code == 202
    assert recover_response.json()["recovered_jobs"] == 1
    assert dispatched_ids == [str(user_job.id)]
