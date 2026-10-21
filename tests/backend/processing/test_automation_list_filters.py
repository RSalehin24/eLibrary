from datetime import timedelta

import pytest
from apps.accounts.models import User
from apps.processing.automation_models import SourceAutomation
from apps.processing.job_models import BackgroundJob

pytestmark = pytest.mark.django_db
URL = "/api/v1/manage/automations/"


def another_schedule(automation, **values):
    return SourceAutomation.objects.create(
        run_as=automation.run_as,
        first_run_at=automation.first_run_at,
        next_run_at=automation.next_run_at + timedelta(days=1),
        **values,
    )


def test_schedule_search_state_frequency_and_pages_use_the_same_filtered_total(
    automation, client
):
    another_schedule(automation, name="Daily paused", enabled=False, frequency="daily")
    weekly = another_schedule(
        automation, name="Weekly active", enabled=True, frequency="weekly"
    )
    client.force_login(automation.run_as)
    payload = client.get(
        URL, {"q": "active", "enabled": "enabled", "frequency": "weekly", "limit": 1}
    ).json()
    assert [entry["id"] for entry in payload["entries"]] == [str(weekly.pk)]
    assert payload["pagination"] == {"page": 1, "limit": 1, "total_count": 1}
    assert not BackgroundJob.objects.exists()


def test_due_sort_places_enabled_schedules_first_with_stable_id_ties(
    automation, client
):
    later = another_schedule(automation, name="Later", enabled=True, frequency="daily")
    paused = another_schedule(
        automation, name="Paused", enabled=False, frequency="daily"
    )
    client.force_login(automation.run_as)
    first = client.get(URL, {"sort": "next_run", "limit": 1}).json()
    second = client.get(URL, {"sort": "next_run", "limit": 1, "page": 2}).json()
    assert first["entries"][0]["id"] == str(automation.pk)
    assert second["entries"][0]["id"] == str(later.pk)
    assert first["pagination"]["total_count"] == 3
    assert client.get(URL, {"enabled": "disabled"}).json()["entries"][0]["id"] == str(
        paused.pk
    )


@pytest.mark.parametrize(
    "values",
    [
        {"enabled": "invalid"},
        {"frequency": "invalid"},
        {"sort": "invalid"},
        {"q": "x" * 151},
    ],
)
def test_invalid_schedule_filters_return_validation_errors(automation, client, values):
    client.force_login(automation.run_as)
    assert client.get(URL, values).status_code == 400


def test_reader_cannot_use_schedule_filters_to_view_management_records(
    automation, client
):
    reader = User.objects.create_user(email="schedule-filter-reader@example.test")
    client.force_login(reader)
    assert client.get(URL, {"q": automation.name}).status_code == 403
