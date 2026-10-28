import time as time_module

import pytest
from apps.catalog.models import Book
from apps.processing.models import BookCreationRequest, BookRecord

from tests.backend.processing.test_processing_api_cases.helpers import (
    advance_processing_pipeline,
    login_processing_admin,
)


@pytest.mark.django_db
def test_processing_create_again_reuses_own_linked_book_and_finishes_created(
    client,
    monkeypatch,
):
    login_processing_admin(client)
    existing_book = Book.objects.create(title="Existing Created Book", state="ready")
    record = BookRecord.objects.create(
        id="recreate-created-record",
        name="Recreate Created",
        url="https://www.example.com/books/recreate-created/",
        category="Fiction",
        writer="Writer",
        publisher="Press",
        book_creation_state="deleted",
        linked_book=existing_book,
    )
    processing_request = BookCreationRequest.objects.create(
        id="recreate-created-request",
        book_record=record,
        state="deleted",
        linked_book=existing_book,
    )

    monkeypatch.setattr(
        "apps.processing.service_modules.request_processing_pipeline.capture_source_page_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.runtime_dependencies.capture_source_page_metadata",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.processing_state_queries.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: existing_book,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.request_processing_pipeline.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: existing_book,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.runtime_dependencies.find_existing_book_by_source_url",
        lambda *_args, **_kwargs: existing_book,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.request_processing_pipeline.find_exact_existing_book",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.runtime_dependencies.find_exact_existing_book",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.request_processing_pipeline.detect_metadata_duplicate",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.runtime_dependencies.detect_metadata_duplicate",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.request_processing_pipeline.scrape_book",
        lambda *_args, **_kwargs: {"book_info": "", "main_content": "<p>body</p>"},
        raising=False,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.runtime_dependencies.scrape_book",
        lambda *_args, **_kwargs: {"book_info": "", "main_content": "<p>body</p>"},
        raising=False,
    )
    monkeypatch.setattr(
        "apps.processing.service_modules.request_processing_persistence._persist_processing_book",
        lambda *_args, **_kwargs: existing_book,
    )

    response = client.post(
        "/api/processing/requests/action/",
        {"ids": [processing_request.id], "action": "create_again"},
        content_type="application/json",
    )
    assert response.status_code == 200

    for _ in range(10):
        _mutation, _payload = advance_processing_pipeline(client)
        processing_request.refresh_from_db()
        if processing_request.state == BookCreationRequest.State.CREATED:
            break
        time_module.sleep(0.1)

    processing_request.refresh_from_db()
    record.refresh_from_db()
    assert processing_request.state == "created"
    assert processing_request.linked_book_id == existing_book.id
    assert processing_request.duplicate_of_request_id is None
    assert processing_request.duplicate_of_record_id is None
    assert record.book_creation_state == "created"
    assert record.linked_book_id == existing_book.id
    assert record.is_duplicate is False
    assert record.duplicate_of_record_id is None
