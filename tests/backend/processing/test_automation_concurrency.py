import pytest
from apps.processing.automation_models import AutomationRun
from apps.processing.automations.scheduler import schedule_due_automation
from apps.processing.job_models import BackgroundJob, JobDispatch
from automation_fixtures import NOW
from test_background_job_concurrency import concurrent_calls

pytestmark = pytest.mark.django_db(transaction=True)


def due_at_barrier(identifier):
    return schedule_due_automation(identifier, NOW)


def test_parallel_schedulers_persist_one_occurrence_and_dispatch(automation):
    results = concurrent_calls(due_at_barrier, [automation.pk, automation.pk])
    assert sum(run is not None for run in results) == 1
    assert (
        AutomationRun.objects.count()
        == BackgroundJob.objects.count()
        == JobDispatch.objects.count()
        == 1
    )
