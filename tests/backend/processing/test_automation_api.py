from datetime import timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

import pytest
from apps.accounts.models import User
from apps.processing.automation_models import SourceAutomation
from django.test import Client
from django.utils import timezone

pytestmark = pytest.mark.django_db
PATH = "/api/v1/manage/automations/"


@pytest.fixture
def actor():
    return User.objects.create_user(
        email="automation-admin@library.test", is_staff=True
    )


@pytest.fixture
def values():
    local = (timezone.now() + timedelta(days=1)).astimezone(ZoneInfo("Asia/Dhaka"))
    return {
        "operation_id": str(uuid4()),
        "name": "নতুন বই সংগ্রহ",
        "enabled": True,
        "frequency": "daily",
        "first_run_local": local.strftime("%Y-%m-%dT%H:%M"),
        "time_zone": "Asia/Dhaka",
        "source_max_pages": 20,
        "processing_limit": 10,
    }


def test_create_replay_and_compare_and_swap_updates(actor, values, client):
    client.force_login(actor)
    created = client.post(PATH, values, content_type="application/json")
    assert created.status_code == 201
    replay = client.post(PATH, values, content_type="application/json")
    assert (
        replay.json()["id"] == created.json()["id"]
        and SourceAutomation.objects.count() == 1
    )
    updated = {
        **values,
        "name": "পরিবর্তিত",
        "enabled": False,
        "expected_updated_at": created.json()["updated_at"],
    }
    updated.pop("operation_id")
    detail = f"{PATH}{created.json()['id']}/"
    assert (
        client.patch(detail, updated, content_type="application/json").status_code
        == 200
    )
    assert (
        client.patch(detail, updated, content_type="application/json").status_code
        == 409
    )
    assert client.get(PATH)["Cache-Control"] == "private, no-store"
    assert client.get(detail)["X-Robots-Tag"] == "noindex"


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("frequency", "hourly"),
        ("source_max_pages", 0),
        ("source_max_pages", 201),
        ("processing_limit", 101),
        ("time_zone", "Invalid/Zone"),
        ("first_run_local", "2020-01-01T08:00"),
        ("run_as", str(uuid4())),
        ("name", ""),
    ],
)
def test_invalid_commands_do_not_persist(actor, values, client, key, value):
    client.force_login(actor)
    response = client.post(
        PATH, {**values, key: value}, content_type="application/json"
    )
    assert response.status_code == 400 and not SourceAutomation.objects.exists()


def test_non_object_input_is_a_field_error(actor, client):
    client.force_login(actor)
    assert client.post(PATH, [], content_type="application/json").status_code == 400


def test_commands_require_csrf_and_processing_authority(actor, values, client):
    secure = Client(enforce_csrf_checks=True)
    secure.force_login(actor)
    assert secure.post(PATH, values, content_type="application/json").status_code == 403
    reader = User.objects.create_user(email="automation-reader@library.test")
    client.force_login(reader)
    assert client.get(PATH).status_code == 403
    assert client.post(PATH, values, content_type="application/json").status_code == 403


def test_create_replay_remains_idempotent_after_the_first_run_time(
    actor, values, client, monkeypatch
):
    client.force_login(actor)
    assert client.post(PATH, values, content_type="application/json").status_code == 201
    later = timezone.now() + timedelta(days=2)
    monkeypatch.setattr(
        "apps.processing.automations.serializers.timezone.now", lambda: later
    )
    assert client.post(PATH, values, content_type="application/json").status_code == 201
    assert SourceAutomation.objects.count() == 1


def test_nonexistent_daylight_saving_start_is_an_inline_error(actor, values, client):
    client.force_login(actor)
    values.update(time_zone="America/New_York", first_run_local="2035-03-11T02:30")
    response = client.post(PATH, values, content_type="application/json")
    assert response.status_code == 400
    assert response.json()["field_errors"]["first_run_local"]
