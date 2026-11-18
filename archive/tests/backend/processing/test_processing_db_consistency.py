import pytest
from django.db import connection
from django.utils import timezone

from apps.catalog.models import Book
from apps.processing.models import BookCreationRequest, BookRecord


@pytest.mark.django_db
def test_request_state_bulk_updates_are_mirrored_to_book_record():
    record = BookRecord.objects.create(
        id="trigger-bulk-record",
        name="Trigger Bulk Record",
        url="https://example.test/books/trigger-bulk-record",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="not_created",
    )
    request = BookCreationRequest.objects.create(
        id="trigger-bulk-request",
        book_record=record,
        state="initial",
    )

    record.refresh_from_db()
    assert record.book_creation_state == "initial"

    BookCreationRequest.objects.filter(pk=request.pk).update(
        state="failed",
        updated_at=timezone.now(),
    )

    record.refresh_from_db()
    assert record.book_creation_state == "failed"


@pytest.mark.django_db
def test_raw_sql_request_updates_and_record_overrides_keep_state_consistent():
    linked_book = Book.objects.create(title="Trigger Created Book", state="ready")
    record = BookRecord.objects.create(
        id="trigger-raw-record",
        name="Trigger Raw Record",
        url="https://example.test/books/trigger-raw-record",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="not_created",
        linked_book=linked_book,
    )
    request = BookCreationRequest.objects.create(
        id="trigger-raw-request",
        book_record=record,
        state="queued",
    )

    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE processing_bookcreationrequest
            SET state = %s, updated_at = NOW()
            WHERE id = %s
            """,
            ["created", request.id],
        )

    record.refresh_from_db()
    assert record.book_creation_state == "created"

    BookRecord.objects.filter(pk=record.pk).update(book_creation_state="failed")

    record.refresh_from_db()
    assert record.book_creation_state == "created"
