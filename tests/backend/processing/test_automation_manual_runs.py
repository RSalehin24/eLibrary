from datetime import timedelta
from uuid import uuid4

import pytest
from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.processing.automation_models import AutomationRun
from apps.processing.automations.manual_runs import request_automation_run
from apps.processing.job_models import BackgroundJob, JobDispatch
from automation_fixtures import NOW
from django.test import Client

pytestmark = pytest.mark.django_db


def command(automation):
    return {
        "operation_id": str(uuid4()),
        "expected_updated_at": automation.updated_at.isoformat(),
    }


def endpoint(automation):
    return f"/api/v1/manage/automations/{automation.pk}/runs/"


def prepare_manual(automation, monkeypatch):
    automation.first_run_at = automation.next_run_at = NOW + timedelta(days=1)
    automation.catalog_scope = "unfinished"
    automation.rebuild_updated = True
    automation.process_all = True
    automation.fetch_all = True
    automation.save()
    monkeypatch.setattr(
        "apps.processing.automations.manual_runs.timezone.now", lambda: NOW
    )


@pytest.fixture
def manual_automation(automation, monkeypatch):
    prepare_manual(automation, monkeypatch)
    return automation


def test_manual_run_uses_saved_policy_and_preserves_future_schedule(
    manual_automation, client
):
    automation = manual_automation
    original = (
        automation.next_run_at,
        automation.occurrence_number,
        automation.updated_at,
    )
    client.force_login(automation.run_as)
    values = command(automation)
    response = client.post(
        endpoint(automation), values, content_type="application/json"
    )
    assert response.status_code == 202 and response.json()["state"] == "queued"
    assert (
        client.post(
            endpoint(automation), values, content_type="application/json"
        ).json()
        == response.json()
    )
    run = AutomationRun.objects.get()
    assert (
        run.process_all
        and run.rebuild_updated
        and run.processing_limit == automation.processing_limit
    )
    assert run.job.input["command"]["catalog_scope"] == "unfinished"
    assert run.job.input["command"]["fetch_all"] is True
    assert run.job.requested_by == automation.run_as and run.job.dispatches.count() == 1
    automation.refresh_from_db()
    assert (
        automation.next_run_at,
        automation.occurrence_number,
        automation.updated_at,
    ) == original
    assert BackgroundJob.objects.count() == JobDispatch.objects.count() == 1
    assert set(AuditLog.objects.get().payload) == {"run_id", "revision"}
    assert response["Cache-Control"] == "private, no-store"


def test_disabled_schedule_can_run_once_without_enabling_it(automation, monkeypatch):
    prepare_manual(automation, monkeypatch)
    automation.enabled = False
    automation.process_all = automation.fetch_all = False
    automation.processing_limit = 7
    automation.source_max_pages = 3
    automation.save()
    run = request_automation_run(automation.run_as, automation.pk, command(automation))
    assert run.state == "queued" and run.processing_limit == 7 and not run.process_all
    assert run.job.input["command"]["max_pages"] == 3
    automation.refresh_from_db()
    assert not automation.enabled and automation.next_run_at == NOW + timedelta(days=1)


@pytest.mark.parametrize(
    "changed",
    [{"expected_updated_at": NOW.isoformat()}, {"run_as": 1}, {"process_all": True}],
)
def test_manual_run_rejects_stale_revisions_and_policy_overrides(
    manual_automation, client, changed
):
    automation = manual_automation
    client.force_login(automation.run_as)
    response = client.post(
        endpoint(automation),
        {**command(automation), **changed},
        content_type="application/json",
    )
    assert response.status_code == (409 if "expected_updated_at" in changed else 400)
    assert not BackgroundJob.objects.exists() and not AutomationRun.objects.exists()


def test_manual_run_preserves_owner_authority_and_audits_actual_caller(
    automation, client, monkeypatch
):
    prepare_manual(automation, monkeypatch)
    caller = User.objects.create_user(email="manual-caller@library.test", is_staff=True)
    client.force_login(caller)
    automation.run_as.is_staff = False
    automation.run_as.save()
    response = client.post(
        endpoint(automation), command(automation), content_type="application/json"
    )
    assert response.status_code == 202
    assert (
        response.json()["state"] == "blocked"
        and response.json()["error_code"] == "permission_revoked"
    )
    assert response.json()["job_id"] is None and not BackgroundJob.objects.exists()
    assert AuditLog.objects.get().actor == caller
    automation.refresh_from_db()
    assert automation.run_as_id != caller.pk


def test_manual_run_requires_current_permission_and_csrf(
    automation, client, monkeypatch
):
    prepare_manual(automation, monkeypatch)
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(automation.run_as)
    assert (
        strict.post(
            endpoint(automation), command(automation), content_type="application/json"
        ).status_code
        == 403
    )
    reader = User.objects.create_user(email="manual-reader@library.test")
    client.force_login(reader)
    assert (
        client.post(
            endpoint(automation), command(automation), content_type="application/json"
        ).status_code
        == 403
    )
    assert not AutomationRun.objects.exists()


def test_active_discovery_blocks_a_second_run_without_changing_schedule(
    automation, monkeypatch
):
    prepare_manual(automation, monkeypatch)
    first = request_automation_run(
        automation.run_as, automation.pk, command(automation)
    )
    monkeypatch.setattr(
        "apps.processing.automations.manual_runs.timezone.now",
        lambda: NOW + timedelta(seconds=1),
    )
    second = request_automation_run(
        automation.run_as, automation.pk, command(automation)
    )
    assert first.state == "queued" and second.error_code == "discovery_already_active"
    assert BackgroundJob.objects.count() == 1 and AutomationRun.objects.count() == 2


def test_manual_run_cannot_collide_with_a_scheduled_occurrence(
    automation, client, monkeypatch
):
    monkeypatch.setattr(
        "apps.processing.automations.manual_runs.timezone.now", lambda: NOW
    )
    client.force_login(automation.run_as)
    response = client.post(
        endpoint(automation), command(automation), content_type="application/json"
    )
    assert response.status_code == 409
    assert not BackgroundJob.objects.exists() and not AutomationRun.objects.exists()


def test_manual_run_replay_after_schedule_edit_does_not_run_new_settings(
    automation, monkeypatch
):
    prepare_manual(automation, monkeypatch)
    values = command(automation)
    run = request_automation_run(automation.run_as, automation.pk, values)
    automation.process_all = False
    automation.save()
    repeated = request_automation_run(automation.run_as, automation.pk, values)
    assert repeated.pk == run.pk and repeated.process_all
    assert BackgroundJob.objects.count() == AutomationRun.objects.count() == 1


def test_manual_operation_identifier_is_bound_to_caller(
    automation, client, monkeypatch
):
    prepare_manual(automation, monkeypatch)
    values = command(automation)
    request_automation_run(automation.run_as, automation.pk, values)
    other = User.objects.create_user(
        email="other-run-caller@library.test", is_staff=True
    )
    client.force_login(other)
    assert (
        client.post(
            endpoint(automation), values, content_type="application/json"
        ).status_code
        == 409
    )
    assert BackgroundJob.objects.count() == AutomationRun.objects.count() == 1
