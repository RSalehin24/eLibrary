from typing import Protocol
from urllib.parse import urlsplit

from kombu.exceptions import OperationalError

from apps.processing.jobs.dispatches import DispatchLease

BROKER_CONNECT_TIMEOUT_SECONDS = 5
BROKER_CONFIRM_TIMEOUT_SECONDS = 10
BACKGROUND_JOB_TASK = "apps.processing.tasks.run_background_job_task"


class PublishUnavailable(RuntimeError):
    pass


class JobPublisher(Protocol):
    def publish(self, lease: DispatchLease) -> None: ...


class AMQPPublisher:
    def __init__(self, application):
        broker_url = application.conf.broker_write_url or application.conf.broker_url
        if not isinstance(broker_url, str) or urlsplit(broker_url).scheme not in {
            "amqp",
            "amqps",
            "pyamqp",
        }:
            raise ValueError("The job dispatcher requires an AMQP broker.")
        result_backend = getattr(application.conf, "result_backend", None)
        if isinstance(result_backend, str) and urlsplit(result_backend).scheme in {
            "amqp",
            "amqps",
            "pyamqp",
        }:
            raise ValueError(
                "Set an explicit supported Celery result backend; AMQP is task transport."
            )
        self.application = application

    def publish(self, lease: DispatchLease) -> None:
        try:
            with (
                self.application.connection_for_write(
                    connect_timeout=BROKER_CONNECT_TIMEOUT_SECONDS,
                    transport_options={"confirm_publish": True},
                ) as connection,
                self.application.amqp.Producer(connection) as producer,
            ):
                self.application.send_task(
                    BACKGROUND_JOB_TASK,
                    args=[str(lease.identifier)],
                    task_id=str(lease.identifier),
                    queue=lease.queue,
                    producer=producer,
                    serializer="json",
                    delivery_mode=2,
                    retry=False,
                    ignore_result=True,
                    timeout=BROKER_CONFIRM_TIMEOUT_SECONDS,
                    confirm_timeout=BROKER_CONFIRM_TIMEOUT_SECONDS,
                )
        except (OperationalError, OSError, TimeoutError) as error:
            raise PublishUnavailable("Broker publication was not confirmed.") from error
