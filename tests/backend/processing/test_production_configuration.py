import os
import subprocess
import sys
from copy import deepcopy

import pytest
from config.production import validate_production_settings
from config.settings import database_config
from django.core.exceptions import ImproperlyConfigured


@pytest.fixture
def production_values():
    return {
        "APP_ENV": "production",
        "DEBUG": False,
        "SECRET_KEY": "synthetic-test-key-only-" * 4,
        "CELERY_TASK_ALWAYS_EAGER": False,
        "SESSION_COOKIE_SECURE": True,
        "CSRF_COOKIE_SECURE": True,
        "SECURE_SSL_REDIRECT": True,
        "LEGACY_API_ENABLED": False,
        "LEGACY_ENGINE_ENABLED": False,
        "ALLOWED_HOSTS": ["library.example.test", "api"],
        "PUBLIC_BASE_URL": "https://library.example.test",
        "PUBLIC_API_ORIGIN": "https://library.example.test",
        "FRONTEND_BASE_URL": "https://library.example.test",
        "DATABASES": {
            "default": {
                "HOST": "postgres",
                "USER": "library",
                "PASSWORD": "synthetic-database-password",
            }
        },
        "CELERY_BROKER_URL": "amqp://library:synthetic-broker-password@rabbitmq/library",
        "REDIS_CACHE_URL": "redis://:synthetic-cache-password@redis/1",
    }


def test_secure_production_configuration_passes_without_network(production_values):
    validate_production_settings(production_values)


def test_matching_nonstandard_https_ports_are_supported(production_values):
    for name in ("PUBLIC_BASE_URL", "PUBLIC_API_ORIGIN", "FRONTEND_BASE_URL"):
        production_values[name] = "https://library.example.test:18443"
    validate_production_settings(production_values)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("DEBUG", True),
        ("CELERY_TASK_ALWAYS_EAGER", True),
        ("SECRET_KEY", "development-only-insecure-secret-key"),
        ("SESSION_COOKIE_SECURE", False),
        ("CSRF_COOKIE_SECURE", False),
        ("SECURE_SSL_REDIRECT", False),
        ("LEGACY_API_ENABLED", True),
        ("LEGACY_ENGINE_ENABLED", True),
        ("ALLOWED_HOSTS", ["*"]),
        ("PUBLIC_BASE_URL", "http://library.example.test"),
        ("FRONTEND_BASE_URL", "https://other.example.test"),
        ("PUBLIC_API_ORIGIN", "https://library.example.test/subpath"),
        ("PUBLIC_API_ORIGIN", "https://library.example.test:invalid"),
        ("PUBLIC_API_ORIGIN", "https://library.example.test:0"),
        ("PUBLIC_API_ORIGIN", "https://library.example.test:18443"),
        ("CELERY_BROKER_URL", "redis://:synthetic-cache-password@redis/0"),
        (
            "CELERY_BROKER_URL",
            "amqp://guest:synthetic-broker-password@rabbitmq/library",
        ),
        ("REDIS_CACHE_URL", "redis://redis/1"),
    ],
)
def test_insecure_defaults_fail_without_disclosing_values(
    production_values, key, value
):
    production_values[key] = value
    with pytest.raises(ImproperlyConfigured) as error:
        validate_production_settings(production_values)
    assert "synthetic" not in str(error.value)


def test_short_database_credentials_fail(production_values):
    values = deepcopy(production_values)
    values["DATABASES"]["default"]["PASSWORD"] = "short"
    with pytest.raises(ImproperlyConfigured, match="DATABASE_URL"):
        validate_production_settings(values)


def test_development_configuration_keeps_local_services():
    validate_production_settings({"APP_ENV": "development"})


def test_production_startup_fails_before_serving_with_default_secret():
    environment = {
        **os.environ,
        "APP_ENV": "production",
        "DJANGO_SECRET_KEY": "",
        "PYTHONPATH": "app/backend",
    }
    result = subprocess.run(
        [sys.executable, "-c", "import config.settings"],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode != 0 and "DJANGO_SECRET_KEY" in result.stderr


def test_database_urls_decode_escaped_credentials_and_names():
    values = database_config(
        "postgresql://library%2Breader:test%40password%3Avalue@localhost/library%20test"
    )
    assert values["USER"] == "library+reader"
    assert values["PASSWORD"] == "test@password:value"
    assert values["NAME"] == "library test"


def test_real_production_router_excludes_legacy_endpoints(production_values):
    origin = production_values["PUBLIC_BASE_URL"]
    environment = {
        **os.environ,
        "APP_ENV": "production",
        "DJANGO_DEBUG": "false",
        "DJANGO_SECRET_KEY": production_values["SECRET_KEY"],
        "PUBLIC_BASE_URL": origin,
        "PUBLIC_API_ORIGIN": origin,
        "FRONTEND_BASE_URL": origin,
        "DATABASE_URL": "postgresql://library:synthetic-database-password@postgres/library",
        "CELERY_BROKER_URL": production_values["CELERY_BROKER_URL"],
        "REDIS_CACHE_URL": production_values["REDIS_CACHE_URL"],
        "SESSION_COOKIE_SECURE": "true",
        "CSRF_COOKIE_SECURE": "true",
        "DJANGO_SECURE_SSL_REDIRECT": "true",
        "CELERY_TASK_ALWAYS_EAGER": "false",
        "LEGACY_API_ENABLED": "false",
        "LEGACY_ENGINE_ENABLED": "false",
        "PYTHONPATH": "app/backend",
        "DJANGO_SETTINGS_MODULE": "config.settings",
    }
    script = """
import django
django.setup()
import sys
from config.celery import app
assert 'apps.ingestion.signals' not in sys.modules
for queue in [app.control.mailbox.get_queue('test-worker'), app.control.mailbox.get_reply_queue()]:
    assert queue.durable and queue.expires and not queue.exclusive
assert app.conf.event_queue_exclusive
from django.urls import Resolver404, resolve
assert resolve('/api/v1/health/live/').url_name == 'liveness'
assert resolve('/admin/login/').url_name == 'login'
for path in ['/api/auth/demo-login/', '/api/catalog/books/', '/api/access/books/']:
    try:
        resolve(path)
    except Resolver404:
        continue
    raise RuntimeError('A legacy route is exposed in production.')
"""
    result = subprocess.run(
        [sys.executable, "-c", script],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "Production URL configuration failed."
