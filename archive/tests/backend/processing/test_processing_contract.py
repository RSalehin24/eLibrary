import pytest
from django.contrib import admin
from django.conf import settings
from django.test import RequestFactory

from apps.accounts.models import User
from apps.processing.models import (
    BookCreationRequest,
    BookCreationRequestState,
    BookCreationState,
    BookRecord,
    ProcessingAutomationSettings,
    ProcessingSyncState,
    ProcessingUiDomainVersion,
    ProcessingUiProjection,
)
from config.celery import app as celery_app


def choice_values(field):
    return {value for value, _label in field.choices}


def model_field_names(model):
    return {field.name for field in model._meta.get_fields()}


@pytest.mark.django_db
def test_processing_models_match_expected_contract():
    assert {
        "id",
        "name",
        "url",
        "category",
        "writer",
        "translator",
        "composer",
        "publisher",
        "created_at",
        "updated_at",
        "book_creation_state",
    }.issubset(model_field_names(BookRecord))
    assert {
        "id",
        "book_record",
        "state",
        "created_at",
        "updated_at",
        "progress",
        "error_message",
        "is_resumed",
        "is_confirmed_not_duplicate",
        "duplicate_of_request",
        "duplicate_of_record",
        "linked_book",
    }.issubset(model_field_names(BookCreationRequest))
    assert BookCreationRequest._meta.get_field("book_record").remote_field.model is BookRecord
    assert choice_values(BookRecord._meta.get_field("book_creation_state")) == set(BookCreationState.values)
    assert choice_values(BookCreationRequest._meta.get_field("state")) == set(
        BookCreationRequestState.values
    )
    assert {"domain", "version", "created_at", "updated_at"}.issubset(
        model_field_names(ProcessingUiDomainVersion)
    )
    assert {"key", "payload", "created_at", "updated_at"}.issubset(
        model_field_names(ProcessingUiProjection)
    )


@pytest.mark.django_db
def test_processing_optional_fields_support_saved_progress_and_duplicate_links():
    request_field = BookCreationRequest._meta.get_field

    assert request_field("progress").null is True
    assert request_field("duplicate_of_request").null is True
    assert request_field("duplicate_of_record").null is True
    assert request_field("linked_book").null is True
    assert request_field("error_message").blank is True


@pytest.mark.django_db
def test_processing_models_are_registered_in_admin_with_core_fields():
    request_factory = RequestFactory()
    request = request_factory.get("/admin/")
    request.user = User.objects.create_superuser(
        email="processing-admin-contract@example.com",
        password="strong-password-123",
    )

    expected_fields = {
        BookRecord: {
            "id",
            "name",
            "url",
            "category",
            "writer",
            "translator",
            "composer",
            "publisher",
            "book_creation_state",
            "linked_book",
            "was_incomplete",
            "resolved_from_incomplete",
            "will_resolve_to_category",
            "is_duplicate",
            "duplicate_of_record",
            "created_at",
            "updated_at",
        },
        BookCreationRequest: {
            "id",
            "book_record",
            "state",
            "progress",
            "error_message",
            "is_resumed",
            "is_confirmed_not_duplicate",
            "duplicate_of_request",
            "duplicate_of_record",
            "duplicate_confirmed",
            "linked_book",
            "pipeline_outcome",
            "created_at",
            "updated_at",
        },
        ProcessingSyncState: {
            "singleton_key",
            "status",
            "progress",
            "remote_pages",
            "page_index",
            "fetched_count",
            "skipped_count",
            "updated_count",
            "appended_count",
            "message",
            "created_at",
            "updated_at",
        },
        ProcessingAutomationSettings: {
            "kind",
            "enabled",
            "interval",
            "time",
            "saved",
            "last_run_at",
            "status_message",
            "created_at",
            "updated_at",
        },
        ProcessingUiDomainVersion: {
            "domain",
            "version",
            "created_at",
            "updated_at",
        },
        ProcessingUiProjection: {
            "key",
            "payload",
            "created_at",
            "updated_at",
        },
    }

    for model, fields in expected_fields.items():
        assert model in admin.site._registry
        model_admin = admin.site._registry[model]
        assert fields.issubset(set(model_admin.get_fields(request)))


def test_processing_related_celery_tasks_are_discoverable():
    celery_app.loader.import_default_modules()
    assert "apps.processing.tasks.run_processing_sync_task" in celery_app.tasks
    assert "apps.processing.tasks.kickoff_book_creation_request_task" in celery_app.tasks
    assert "apps.ingestion.tasks.run_catalog_automation_schedule_task" in celery_app.tasks
    assert "apps.ingestion.tasks.recover_stale_processing_jobs_task" in celery_app.tasks


def test_debug_frontend_origin_range_includes_live_dev_port_5181():
    assert "http://127.0.0.1:5181" in settings.CSRF_TRUSTED_ORIGINS
    assert "http://localhost:5181" in settings.CORS_ALLOWED_ORIGINS


@pytest.mark.django_db
def test_processing_endpoints_require_processing_access(client):
    response = client.get("/api/processing/state/")
    assert response.status_code == 403

    regular_user = User.objects.create_user(
        email="viewer@example.com",
        password="strong-password-123",
    )
    client.force_login(regular_user)

    response = client.get("/api/processing/state/")
    assert response.status_code == 403
