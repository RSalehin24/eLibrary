import pytest
from apps.ingestion.engine.redis_client import get_redis_url
from celery.events.receiver import EventReceiver
from config.celery import app


def test_worker_control_and_event_queues_work_with_current_rabbitmq():
    control = app.control.mailbox.get_queue("configuration-test")
    events = EventReceiver(None, app=app, node_id="configuration-test").queue
    assert control.durable or control.exclusive
    assert events.durable or events.exclusive


@pytest.fixture
def isolated_redis_environment(monkeypatch):
    for key in [
        "REDIS_URL",
        "PROCESSING_CHECKPOINT_REDIS_URL",
        "CELERY_RESULT_BACKEND",
        "CELERY_BROKER_URL",
    ]:
        monkeypatch.delenv(key, raising=False)
    return monkeypatch


@pytest.mark.parametrize(
    "key", ["REDIS_URL", "PROCESSING_CHECKPOINT_REDIS_URL", "CELERY_RESULT_BACKEND"]
)
def test_redis_engine_uses_redis_state_when_tasks_use_amqp(
    isolated_redis_environment, key
):
    isolated_redis_environment.setenv("CELERY_BROKER_URL", "amqp://broker.test/library")
    isolated_redis_environment.setenv(key, "redis://cache.test/2")
    assert get_redis_url() == "redis://cache.test/2"


def test_redis_engine_retains_legacy_redis_brokers_and_rejects_amqp_as_state(
    isolated_redis_environment,
):
    isolated_redis_environment.setenv(
        "CELERY_BROKER_URL", "redis://legacy-cache.test/0"
    )
    assert get_redis_url() == "redis://legacy-cache.test/0"
    isolated_redis_environment.setenv("CELERY_BROKER_URL", "amqp://broker.test/library")
    assert get_redis_url().startswith("redis://")
