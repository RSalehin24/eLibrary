from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def fail_setting(name):
    raise ImproperlyConfigured(f"Configure a secure production value for {name}.")


def checked_url(value, name):
    try:
        url = urlsplit(value)
        _ = url.port
    except ValueError:
        fail_setting(name)
    return url


def checked_origin(value, name):
    url = checked_url(value, name)
    if (
        url.scheme != "https"
        or url.port == 0
        or not url.hostname
        or url.username
        or url.password
        or url.query
        or url.fragment
        or url.path not in {"", "/"}
    ):
        fail_setting(name)
    return url.netloc


def require_service_credentials(value, name):
    url = checked_url(value, name)
    if not url.hostname or not url.password or len(unquote(url.password)) < 16:
        fail_setting(name)
    return url


def validate_production_settings(values):
    if values["APP_ENV"] != "production":
        return
    key = values["SECRET_KEY"]
    if len(key) < 50 or len(set(key)) < 5 or key.startswith("development-"):
        fail_setting("DJANGO_SECRET_KEY")
    if values["DEBUG"] or values["CELERY_TASK_ALWAYS_EAGER"]:
        fail_setting("DJANGO_DEBUG / CELERY_TASK_ALWAYS_EAGER")
    if not values["SESSION_COOKIE_SECURE"] or not values["CSRF_COOKIE_SECURE"]:
        fail_setting("SESSION_COOKIE_SECURE / CSRF_COOKIE_SECURE")
    if not values["SECURE_SSL_REDIRECT"]:
        fail_setting("DJANGO_SECURE_SSL_REDIRECT")
    if values["LEGACY_API_ENABLED"]:
        fail_setting("LEGACY_API_ENABLED")
    if values["LEGACY_ENGINE_ENABLED"]:
        fail_setting("LEGACY_ENGINE_ENABLED")
    if "*" in values["ALLOWED_HOSTS"]:
        fail_setting("DJANGO_ALLOWED_HOSTS")
    origins = {
        checked_origin(values[name], name)
        for name in ("PUBLIC_BASE_URL", "PUBLIC_API_ORIGIN", "FRONTEND_BASE_URL")
    }
    if len(origins) != 1:
        fail_setting("same-origin public URLs")
    validate_production_services(values)


def validate_production_services(values):
    database = values["DATABASES"]["default"]
    if (
        not database["HOST"]
        or not database["USER"]
        or not database["PASSWORD"]
        or len(database["PASSWORD"]) < 16
    ):
        fail_setting("DATABASE_URL")
    broker = require_service_credentials(
        values["CELERY_BROKER_URL"], "CELERY_BROKER_URL"
    )
    if broker.scheme not in {"amqp", "amqps"} or unquote(broker.username or "") in {
        "",
        "guest",
    }:
        fail_setting("CELERY_BROKER_URL")
    cache = require_service_credentials(values["REDIS_CACHE_URL"], "REDIS_CACHE_URL")
    if cache.scheme not in {"redis", "rediss"}:
        fail_setting("REDIS_CACHE_URL")
