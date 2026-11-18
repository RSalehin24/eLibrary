import json
import time as time_module
from datetime import time, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.db import IntegrityError
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Book
from apps.ingestion.models import BookSubmission, ProcessingJob, SourceCatalogEntry
from apps.processing import services as processing_services
from apps.processing.models import (
    BookCreationRequest,
    BookRecord,
    ProcessingAutomationKind,
    ProcessingAutomationSettings,
    ProcessingSyncStatus,
)
from apps.processing.services import (
    PROCESSING_SYNC_KEY_CATALOG,
    PROCESSING_SYNC_KEY_INCOMPLETE,
    dispatch_sync_task,
    get_sync_state,
)
from apps.processing.tasks import (
    kickoff_book_creation_request_task,
    run_processing_sync_task,
)


def login_processing_admin(client, email="processing-admin@example.com"):
    user = User.objects.create_superuser(
        email=email,
        password="strong-password-123",
    )
    client.force_login(user)
    return user


def record_payload(record_id, **overrides):
    payload = {
        "id": record_id,
        "name": f"{record_id} title",
        "url": f"https://example.test/books/{record_id}",
        "category": "Fiction",
        "writer": "Writer One",
        "translator": "",
        "composer": "",
        "publisher": "Example Press",
        "updatedAt": timezone.now().isoformat(),
    }
    payload.update(overrides)
    return payload


def rebuild_processing_ui_state():
    processing_services.rebuild_processing_ui_state()


def processing_state_payload(client, *, include_lists=True):
    query = "" if include_lists else "?includeLists=0"
    response = client.get(f"/api/processing/state/{query}")
    assert response.status_code == 200
    return response.json()


def processing_mutation(client, previous_versions, *, include_lists=False, extra=None):
    rebuild_processing_ui_state()
    changed_versions, _ = processing_services.processing_ui_versions_diff(
        previous_versions,
        domains=processing_services.PROCESSING_CARD_KEYS,
    )
    mutation = {
        "ok": True,
        "versions": changed_versions,
    }
    if extra:
        mutation.update(extra)
    return mutation, processing_state_payload(client, include_lists=include_lists)


def post_processing_mutation(
    client,
    path,
    body=None,
    *,
    include_lists=False,
):
    if path == "/api/processing/pipeline/advance/":
        previous_versions = processing_services.processing_ui_versions_map(
            domains=processing_services.PROCESSING_CARD_KEYS
        )
        advanced = processing_services.advance_pipeline_once()
        return processing_mutation(
            client,
            previous_versions,
            include_lists=include_lists,
            extra={"advancedCount": advanced},
        )

    if path == "/api/processing/sync/advance/" or (
        path.startswith("/api/processing/sync/")
        and path.endswith("/advance/")
    ):
        scope = None
        if path != "/api/processing/sync/advance/":
            scope = path.removeprefix("/api/processing/sync/").removesuffix("/advance/").strip("/") or None
        previous_versions = processing_services.processing_ui_versions_map(
            domains=processing_services.PROCESSING_CARD_KEYS
        )
        processing_services.advance_sync_once(scope)
        return processing_mutation(
            client,
            previous_versions,
            include_lists=include_lists,
        )

    response = client.post(path, body, content_type="application/json")
    assert response.status_code == 200
    mutation = response.json()
    assert mutation["ok"] is True
    assert "versions" in mutation
    rebuild_processing_ui_state()
    return mutation, processing_state_payload(client, include_lists=include_lists)


def advance_processing_sync(client, *, count=1):
    payload = None
    for _ in range(count):
        _mutation, payload = post_processing_mutation(
            client,
            "/api/processing/sync/advance/",
            include_lists=False,
        )
    return payload


def advance_processing_pipeline(client, *, count=1, include_lists=False):
    mutation = None
    payload = None
    for _ in range(count):
        mutation, payload = post_processing_mutation(
            client,
            "/api/processing/pipeline/advance/",
            include_lists=include_lists,
        )
    return mutation, payload


class FakeProcessingCheckpointRedis:
    def __init__(self, initial=None):
        self.store = dict(initial or {})

    def set(self, key, value):
        self.store[key] = value
        return True

    def delete(self, key):
        self.store.pop(key, None)
        return 1


def set_catalog_runtime_state(
    sync_state,
    *,
    sync_status,
    request_creation_status,
    top_status=None,
    sync_owner="manual",
    request_creation_owner="catalog_automation",
    next_page_index=0,
    fetched_count=0,
    session_id="catalog-matrix-session",
    request_creation=None,
):
    checkpoint_token = processing_services.catalog_sync_checkpoint_token(
        session_id,
        next_page_index=next_page_index,
        fetched_count=fetched_count,
    )
    sync_phase_state = processing_services._catalog_phase_state(
        processing_services.CATALOG_SYNC_PHASE,
        status=sync_status,
        owner=sync_owner if sync_status != "not_started" else "",
        trigger_source=processing_services.SYNC_TRIGGER_SOURCE_BUTTON,
        checkpoint=f"page-{next_page_index}" if sync_status != "not_started" else "",
        saved_data=(
            {
                "runMode": sync_owner,
                "triggerSource": processing_services.SYNC_TRIGGER_SOURCE_BUTTON,
                "sessionId": session_id,
                "checkpointToken": checkpoint_token,
                "nextPageIndex": next_page_index,
                "fetchedCount": fetched_count,
            }
            if sync_status != "not_started"
            else {}
        ),
    )
    request_creation_payload = request_creation
    if request_creation_payload is None and request_creation_status != "not_started":
        request_creation_payload = {
            "baseCheckpointToken": checkpoint_token,
            "lastRecordId": "matrix-record-1",
            "processedCount": 1,
            "createdCount": 1,
            "unsupportedCount": 0,
        }
    request_creation_phase_state = processing_services._catalog_phase_state(
        processing_services.CATALOG_REQUEST_CREATION_PHASE,
        status=request_creation_status,
        owner=request_creation_owner if request_creation_status != "not_started" else "",
        trigger_source=processing_services.SYNC_TRIGGER_SOURCE_BUTTON,
        checkpoint=(
            f"request-{request_creation_payload.get('lastRecordId') or request_creation_payload.get('processedCount', 0)}"
            if request_creation_payload
            else ""
        ),
        request_creation=request_creation_payload,
        base_sync_checkpoint_token=(
            request_creation_payload.get("baseCheckpointToken")
            if request_creation_payload
            else ""
        ),
    )
    phase_states = {
        processing_services.CATALOG_SYNC_PHASE: sync_phase_state,
        processing_services.CATALOG_REQUEST_CREATION_PHASE: request_creation_phase_state,
    }
    sync_state.status = top_status or processing_services.catalog_runtime_status(phase_states)
    sync_state.progress = processing_services.build_catalog_progress_payload(phase_states)
    sync_state.page_index = next_page_index
    sync_state.fetched_count = fetched_count
    sync_state.save(
        update_fields=[
            "status",
            "progress",
            "page_index",
            "fetched_count",
            "updated_at",
        ]
    )
    return sync_state
