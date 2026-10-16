import signal
from io import StringIO
from unittest.mock import Mock

import pytest
from apps.processing.job_models import DispatchState
from apps.processing.management.commands import dispatch_background_jobs
from django.core.management import call_command
from django.core.management.base import CommandError

pytestmark = pytest.mark.django_db(transaction=True)


def test_operator_tick_confirms_dispatches_without_running_work_in_the_command(
    preparation_job, monkeypatch
):
    publisher = Mock()
    monkeypatch.setattr(dispatch_background_jobs, "AMQPPublisher", lambda _: publisher)
    output = StringIO()
    call_command("dispatch_background_jobs", once=True, stdout=output)
    assert publisher.publish.call_count == 1
    assert preparation_job.dispatches.get().state == DispatchState.PUBLISHED
    preparation_job.refresh_from_db()
    assert preparation_job.state == "queued" and preparation_job.attempts.count() == 0
    assert "confirmed=1 pending=0" in output.getvalue()


def test_operator_command_rejects_non_amqp_before_leasing_dispatches(
    preparation_job, monkeypatch
):
    application = Mock()
    application.conf.broker_write_url = None
    application.conf.broker_url = "redis://localhost/0"
    monkeypatch.setattr(dispatch_background_jobs, "app", application)
    with pytest.raises(CommandError, match="AMQP"):
        call_command("dispatch_background_jobs", once=True)
    assert preparation_job.dispatches.get().state == DispatchState.PENDING


@pytest.mark.parametrize("interval", [0, 61])
def test_operator_command_rejects_invalid_intervals(interval):
    with pytest.raises(CommandError, match="between 1 and 60"):
        call_command("dispatch_background_jobs", once=True, interval=interval)


@pytest.mark.parametrize("stop_signal", [signal.SIGTERM, signal.SIGINT])
def test_dispatcher_finishes_current_tick_and_restores_signal_handlers(
    preparation_job, monkeypatch, stop_signal
):
    previous = signal.getsignal(stop_signal)
    publisher = Mock()
    publisher.publish.side_effect = lambda _: signal.raise_signal(stop_signal)
    monkeypatch.setattr(dispatch_background_jobs, "AMQPPublisher", lambda _: publisher)
    call_command("dispatch_background_jobs", interval=60, stdout=StringIO())
    assert publisher.publish.call_count == 1
    assert preparation_job.dispatches.get().state == DispatchState.PUBLISHED
    assert signal.getsignal(stop_signal) == previous
