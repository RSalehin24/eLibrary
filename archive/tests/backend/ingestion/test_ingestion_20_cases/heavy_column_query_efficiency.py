

@pytest.mark.django_db
def test_submission_list_avoids_loading_heavy_linked_book_columns(client):
    admin = User.objects.create_superuser(
        email="submission-list-admin@example.com",
        password="strong-password-123",
    )
    book = Book.objects.create(
        title="ভারী প্রসেসিং বই",
        state="ready",
        review_state="approved",
        summary="Summary",
        raw_scraped_metadata={"source": "seed"},
        raw_scrape_payload={"payload": "seed"},
        main_content_html="<p>Heavy content</p>",
        book_info_html="<p>Book info</p>",
        dedication_html="<p>Dedication</p>",
        toc=[{"label": "One", "href": "#one"}],
        content_items=[{"title": "One", "slug": "one"}],
    )
    submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input="https://example.com/heavy-submission",
        normalized_input="heavy-submission",
        resolved_url="https://example.com/heavy-submission",
        resolution_status="resolved",
        resolution_confidence=1.0,
        status=SubmissionStatus.READY,
        origin=SubmissionOrigin.CURATION,
        linked_book=book,
    )
    ProcessingJob.objects.create(
        submission=submission,
        book=book,
        status=JobStatus.SUCCEEDED,
        payload={"heavy": "payload"},
    )
    client.force_login(admin)

    with CaptureQueriesContext(connection) as captured_queries:
        response = client.get("/api/ingestion/submissions/?limit=1&origin=curation")

    assert response.status_code == 200
    assert_queries_do_not_select_columns(
        captured_queries,
        '"catalog_book"',
        HEAVY_BOOK_COLUMNS,
    )
    assert_queries_do_not_select_columns(
        captured_queries,
        '"ingestion_processingjob"',
        ('"ingestion_processingjob"."payload"',),
    )
    assert_queries_do_not_select_columns(
        captured_queries,
        '"ingestion_titleresolutionattempt"',
        ('"ingestion_titleresolutionattempt"."raw_results"',),
    )


@pytest.mark.django_db
def test_processing_job_list_avoids_loading_heavy_book_columns(client):
    admin = User.objects.create_superuser(
        email="job-list-admin@example.com",
        password="strong-password-123",
    )
    book = Book.objects.create(
        title="ভারী জব বই",
        state="ready",
        review_state="approved",
        summary="Summary",
        raw_scraped_metadata={"source": "seed"},
        raw_scrape_payload={"payload": "seed"},
        main_content_html="<p>Heavy content</p>",
        book_info_html="<p>Book info</p>",
        dedication_html="<p>Dedication</p>",
        toc=[{"label": "One", "href": "#one"}],
        content_items=[{"title": "One", "slug": "one"}],
    )
    submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input="https://example.com/heavy-job",
        normalized_input="heavy-job",
        status=SubmissionStatus.PROCESSING,
        origin=SubmissionOrigin.CURATION,
        linked_book=book,
    )
    ProcessingJob.objects.create(
        submission=submission,
        book=book,
        status=JobStatus.PROCESSING,
        payload={"heavy": "payload"},
    )
    client.force_login(admin)

    with CaptureQueriesContext(connection) as captured_queries:
        response = client.get("/api/ingestion/jobs/?limit=1&origin=curation")

    assert response.status_code == 200
    assert_queries_do_not_select_columns(
        captured_queries,
        '"catalog_book"',
        HEAVY_BOOK_COLUMNS,
    )
    assert_queries_do_not_select_columns(
        captured_queries,
        '"ingestion_processingjob"',
        ('"ingestion_processingjob"."payload"',),
    )


@pytest.mark.django_db
def test_duplicate_review_list_avoids_loading_heavy_book_columns(client):
    admin = User.objects.create_superuser(
        email="duplicate-list-admin@example.com",
        password="strong-password-123",
    )
    linked_book = Book.objects.create(
        title="লিঙ্কড বই",
        state="ready",
        review_state="approved",
        summary="Summary",
        raw_scraped_metadata={"source": "seed"},
        raw_scrape_payload={"payload": "seed"},
        main_content_html="<p>Heavy content</p>",
        book_info_html="<p>Book info</p>",
        dedication_html="<p>Dedication</p>",
        toc=[{"label": "One", "href": "#one"}],
        content_items=[{"title": "One", "slug": "one"}],
    )
    existing_book = Book.objects.create(
        title="বিদ্যমান বই",
        state="ready",
        review_state="approved",
        summary="Summary",
        raw_scraped_metadata={"source": "seed"},
        raw_scrape_payload={"payload": "seed"},
        main_content_html="<p>Heavy content</p>",
        book_info_html="<p>Book info</p>",
        dedication_html="<p>Dedication</p>",
        toc=[{"label": "One", "href": "#one"}],
        content_items=[{"title": "One", "slug": "one"}],
    )
    submission = BookSubmission.objects.create(
        submitter=admin,
        input_type="url",
        original_input="https://example.com/heavy-duplicate",
        normalized_input="heavy-duplicate",
        resolved_url="https://example.com/heavy-duplicate",
        resolution_status="resolved",
        resolution_confidence=1.0,
        status=SubmissionStatus.DUPLICATE,
        origin=SubmissionOrigin.CURATION,
        linked_book=linked_book,
    )
    ProcessingJob.objects.create(
        submission=submission,
        book=linked_book,
        status=JobStatus.FAILED,
        payload={"heavy": "payload"},
    )
    DuplicateReview.objects.create(
        submission=submission,
        existing_book=existing_book,
        raw_evidence={"kind": "source-url"},
    )
    client.force_login(admin)

    with CaptureQueriesContext(connection) as captured_queries:
        response = client.get("/api/ingestion/duplicate-reviews/?limit=1&origin=curation")

    assert response.status_code == 200
    assert_queries_do_not_select_columns(
        captured_queries,
        '"catalog_book"',
        HEAVY_BOOK_COLUMNS,
    )
    assert_queries_do_not_select_columns(
        captured_queries,
        '"ingestion_processingjob"',
        ('"ingestion_processingjob"."payload"',),
    )
    assert_queries_do_not_select_columns(
        captured_queries,
        '"ingestion_titleresolutionattempt"',
        ('"ingestion_titleresolutionattempt"."raw_results"',),
    )
