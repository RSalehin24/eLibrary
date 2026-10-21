from datetime import timedelta
from uuid import uuid4

import pytest
from apps.processing.automation_models import AutomationRun
from apps.processing.automations.manual_runs import request_automation_run
from apps.processing.job_models import BackgroundJob, JobDispatch
from automation_fixtures import NOW
from test_background_job_concurrency import concurrent_calls

pytestmark = pytest.mark.django_db(transaction=True)


def test_concurrent_manual_retries_create_one_run_and_dispatch(automation, monkeypatch):
    automation.next_run_at = NOW + timedelta(days=1)
    automation.save()
    monkeypatch.setattr(
        "apps.processing.automations.manual_runs.timezone.now", lambda: NOW
    )
    values = {
        "operation_id": str(uuid4()),
        "expected_updated_at": automation.updated_at.isoformat(),
    }

    def run(_):
        return request_automation_run(automation.run_as, automation.pk, values)

    results = concurrent_calls(run, [None, None])
    assert results[0].pk == results[1].pk
    assert (
        AutomationRun.objects.count()
        == BackgroundJob.objects.count()
        == JobDispatch.objects.count()
        == 1
    )
