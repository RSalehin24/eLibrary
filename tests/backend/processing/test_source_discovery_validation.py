from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.ingestion.source_discovery.configuration import discovery_configuration
from apps.processing.job_models import BackgroundJob
from django.test import Client

pytestmark = pytest.mark.django_db
PATH = "/api/v1/manage/sources/discovery/"


def configured_client(settings):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_CATALOG_URL = "https://source.test/books/"
    actor = User.objects.create_user(
        email="discovery-validation@library.test", is_staff=True
    )
    client = Client(enforce_csrf_checks=True)
    client.force_login(actor)
    token = client.get("/api/v1/auth/session/").json()["csrf_token"]
    return client, token


def values():
    return {
        "operation_id": str(uuid4()),
        "configuration_revision": discovery_configuration()["configuration_revision"],
        "max_pages": 20,
    }


def test_source_discovery_mutations_require_a_real_csrf_token(settings):
    client, token = configured_client(settings)
    command = values()
    assert (
        client.post(PATH, command, content_type="application/json").status_code == 403
    )
    accepted = client.post(
        PATH, command, content_type="application/json", HTTP_X_CSRFTOKEN=token
    )
    assert accepted.status_code == 202 and BackgroundJob.objects.count() == 1


@pytest.mark.parametrize(
    "invalid",
    [
        {"max_pages": 0},
        {"max_pages": 201},
        {"max_pages": "invalid"},
        {"catalog_url": "https://evil.test/"},
        {"operation_id": "invalid"},
        {"configuration_revision": "0" * 64},
    ],
)
def test_invalid_or_stale_discovery_commands_never_create_a_job(settings, invalid):
    client, token = configured_client(settings)
    response = client.post(
        PATH,
        {**values(), **invalid},
        content_type="application/json",
        HTTP_X_CSRFTOKEN=token,
    )
    assert response.status_code == (409 if "configuration_revision" in invalid else 400)
    if response.status_code == 400:
        assert all(
            isinstance(messages, list)
            and all(isinstance(message, str) for message in messages)
            for messages in response.json()["field_errors"].values()
        )
    assert not BackgroundJob.objects.exists()


def test_missing_or_unsafe_configuration_is_visible_without_exposing_credentials(
    settings,
):
    client, _ = configured_client(settings)
    settings.SOURCE_SITE_CATALOG_URL = "https://user:private-secret@source.test/books/"
    response = client.get(PATH)
    assert response.status_code == 200 and not response.json()["configured"]
    assert (
        response.json()["catalog_url"] is None
        and "private-secret" not in response.content.decode()
    )
    settings.SOURCE_SITE_HOST = ""
    assert client.get(PATH).json()["configured"] is False
