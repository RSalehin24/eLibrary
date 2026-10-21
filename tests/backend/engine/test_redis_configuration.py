import pytest
from apps.ingestion.engine.constants import DEFAULT_REDIS_URL

from .conftest import _get_redis_host


@pytest.fixture
def redis_environment(monkeypatch):
    for name in (
        "REDIS_HOST",
        "REDIS_URL",
        "PROCESSING_CHECKPOINT_REDIS_URL",
        "CELERY_RESULT_BACKEND",
        "CELERY_BROKER_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("CELERY_BROKER_URL", "amqp://127.0.0.1:5672/")


def test_engine_fixture_never_treats_amqp_as_a_redis_hostname(redis_environment):
    assert _get_redis_host() == DEFAULT_REDIS_URL


@pytest.mark.parametrize(
    "name", ["REDIS_URL", "PROCESSING_CHECKPOINT_REDIS_URL", "CELERY_RESULT_BACKEND"]
)
def test_engine_fixture_reuses_configured_redis_backend(
    redis_environment, monkeypatch, name
):
    monkeypatch.setenv(name, "redis://127.0.0.1:56380/15")
    assert _get_redis_host() == "redis://127.0.0.1:56380/15"


def test_engine_fixture_preserves_explicit_test_host_override(
    redis_environment, monkeypatch
):
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:56379/0")
    monkeypatch.setenv("REDIS_HOST", "redis://127.0.0.1:56380/15")
    assert _get_redis_host() == "redis://127.0.0.1:56380/15"
