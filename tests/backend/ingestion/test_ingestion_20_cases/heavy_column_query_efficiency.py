import pytest
from apps.accounts.models import User
from apps.catalog.models import Book
from apps.ingestion.models import (
    BookSubmission,
    JobStatus,
    ProcessingJob,
    SubmissionOrigin,
    SubmissionStatus,
)
from django.db import connection
from django.test.utils import CaptureQueriesContext

from tests.backend.ingestion.test_ingestion_20_cases.activity_tasks_and_schedule import (
    HEAVY_BOOK_COLUMNS,
    assert_queries_do_not_select_columns,
)


@pytest.mark.django_db
def test_submission_list_avoids_loading_heavy_linked_book_columns(client):
    admin = User.objects.create_superuser(
        email="submission-list-admin@example.com",
        password="strong-password-123",
    )
    book = Book.objects.create(
        title="ভারী প্রসেসিং বই",
        state="ready",
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
    from apps.accounts.models import User
    from apps.catalog.models import Book

    actor = User.objects.create_user(email="removed-review@example.test", is_staff=True)
    book = Book.objects.create(title="অপ্রকাশিত বই")
    client.force_login(actor)
    assert client.get("/api/ingestion/duplicate-reviews/").status_code == 404
    assert (
        client.post(f"/api/ingestion/duplicate-reviews/{book.pk}/resolve/").status_code
        == 404
    )
    book.refresh_from_db()
    assert book.state == "draft"
