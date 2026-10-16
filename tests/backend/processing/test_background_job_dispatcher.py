from contextlib import nullcontext
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from apps.processing.job_models import DispatchState
from apps.processing.jobs.broker import (
    BACKGROUND_JOB_TASK,
    AMQPPublisher,
    PublishUnavailable,
)
from apps.processing.jobs.commands import enqueue_job
from apps.processing.jobs.dispatcher import dispatch_available
from apps.processing.jobs.dispatches import DispatchLease
from kombu.exceptions import OperationalError

pytestmark = pytest.mark.django_db


def test_dispatcher_records_partial_broker_outcomes_individually(command):
    first = enqueue_job(command)
    second = enqueue_job(replace(command, identifier=uuid4()))
    failed_identifier = second.dispatches.get().pk
    publisher = Mock()

    def publish(lease):
        if lease.identifier == failed_identifier:
            raise PublishUnavailable("simulated broker interruption")

    publisher.publish.side_effect = publish
    outcome = dispatch_available(publisher)
    assert outcome.confirmed == outcome.pending == 1
    assert first.dispatches.get().state == DispatchState.PUBLISHED
    assert second.dispatches.get().state == DispatchState.PENDING


def fake_application():
    connection, producer = Mock(), Mock()
    application = Mock(
        conf=SimpleNamespace(
            broker_write_url=None, broker_url="amqp://localhost/library-test"
        )
    )
    application.connection_for_write.return_value = nullcontext(connection)
    application.amqp.Producer.return_value = nullcontext(producer)
    return application


def test_amqp_publication_is_confirmed_persistent_bounded_and_contains_only_an_identifier():
    application = fake_application()
    lease = DispatchLease(uuid4(), uuid4(), "delivery")
    AMQPPublisher(application).publish(lease)
    assert application.connection_for_write.call_args.kwargs == {
        "connect_timeout": 5,
        "transport_options": {"confirm_publish": True},
    }
    request = application.send_task.call_args
    assert request.args == (BACKGROUND_JOB_TASK,)
    assert request.kwargs["args"] == [str(lease.identifier)]
    assert (
        request.kwargs["delivery_mode"] == 2 and request.kwargs["serializer"] == "json"
    )
    assert request.kwargs["queue"] == "delivery" and request.kwargs["retry"] is False
    assert request.kwargs["confirm_timeout"] == request.kwargs["timeout"] == 10


@pytest.mark.parametrize(
    "failure", [OperationalError("simulated"), TimeoutError("simulated")]
)
def test_unconfirmed_publication_returns_a_safe_retry_boundary(failure):
    application = fake_application()
    application.send_task.side_effect = failure
    with pytest.raises(PublishUnavailable, match="not confirmed"):
        AMQPPublisher(application).publish(
            DispatchLease(uuid4(), uuid4(), "processing")
        )


def test_dispatcher_rejects_non_amqp_configuration_before_leasing_work():
    application = Mock(
        conf=SimpleNamespace(broker_write_url=None, broker_url="redis://localhost/0")
    )
    with pytest.raises(ValueError, match="AMQP"):
        AMQPPublisher(application)


def test_dispatcher_rejects_an_amqp_result_backend_before_leasing_work():
    application = fake_application()
    application.conf.result_backend = application.conf.broker_url
    with pytest.raises(ValueError, match="result backend"):
        AMQPPublisher(application)
