from pathlib import Path

from config.background_limits import background_limits, processing_queue_name
from config.environment import (
    append_unique,
    database_config,
    env,
    env_bool,
    env_int,
    env_list,
    hostname_from_url,
    normalized_origin,
)
from config.logging import logging_settings
from config.production import validate_production_settings
from config.rest import api_schema_settings, rest_framework_settings

BASE_DIR = Path(__file__).resolve().parent.parent


APP_ENV = env("APP_ENV", "development")
LEGACY_API_ENABLED = env_bool("LEGACY_API_ENABLED", APP_ENV != "production")
LEGACY_ENGINE_ENABLED = env_bool("LEGACY_ENGINE_ENABLED", APP_ENV != "production")
DEBUG = env_bool("DJANGO_DEBUG", APP_ENV != "production")
SECRET_KEY = env("DJANGO_SECRET_KEY", "development-only-insecure-secret-key")
PUBLIC_BASE_URL = env("PUBLIC_BASE_URL", "http://localhost")
FRONTEND_BASE_URL = env("FRONTEND_BASE_URL", PUBLIC_BASE_URL).rstrip("/")
FRONTEND_PORT = env("FRONTEND_PORT", "").strip()
PUBLIC_API_ORIGIN = env("PUBLIC_API_ORIGIN", PUBLIC_BASE_URL).rstrip("/")
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,backend,nginx")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS", "")
CORS_ALLOWED_ORIGINS = env_list("DJANGO_CORS_ALLOWED_ORIGINS", "")
CORS_ALLOW_CREDENTIALS = env_bool("DJANGO_CORS_ALLOW_CREDENTIALS", True)

for host in {
    hostname_from_url(FRONTEND_BASE_URL),
    hostname_from_url(PUBLIC_API_ORIGIN),
}:
    append_unique(ALLOWED_HOSTS, host)

for origin in {
    normalized_origin(FRONTEND_BASE_URL),
    normalized_origin(PUBLIC_API_ORIGIN),
}:
    append_unique(CSRF_TRUSTED_ORIGINS, origin)
    append_unique(CORS_ALLOWED_ORIGINS, origin)

if DEBUG:
    for host in ("localhost", "127.0.0.1"):
        for port in range(5173, 5182):
            origin = f"http://{host}:{port}"
            append_unique(CSRF_TRUSTED_ORIGINS, origin)
            append_unique(CORS_ALLOWED_ORIGINS, origin)

PASSWORD_CREATE_FRONTEND_PATH = env("PASSWORD_CREATE_FRONTEND_PATH", "/create-password")
PASSWORD_RESET_FRONTEND_PATH = env(
    "PASSWORD_RESET_FRONTEND_PATH", "/reset-password/confirm"
)
PASSWORD_RESET_TIMEOUT = env_int("PASSWORD_RESET_TIMEOUT", 6 * 60 * 60)
SUPER_ADMIN_EMAIL = env("SUPER_ADMIN_EMAIL", "library@rsalehin24.me")
SUPER_ADMIN_PASSWORD = env("SUPER_ADMIN_PASSWORD", "")
DEMO_USER_EMAIL = env("DEMO_USER_EMAIL", "demo_user.library@rsalehin24.me")
DEMO_USER_PASSWORD = env("DEMO_USER_PASSWORD", "")
SOURCE_SITE_EMAIL = env("SOURCE_SITE_EMAIL", "")
SOURCE_SITE_PASSWORD = env("SOURCE_SITE_PASSWORD", "")
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL", "RSalehin24 Library <library@rsalehin24.me>"
)
SOURCE_SITE_HOST = env("SOURCE_SITE_HOST", "").strip().lower()
SOURCE_SITE_CATALOG_URL = env("SOURCE_SITE_CATALOG_URL", "").strip()
SOURCE_REQUEST_INTERVAL_SECONDS = env("SOURCE_REQUEST_INTERVAL_SECONDS", "2")
SOURCE_SITE_FALLBACK_HOSTS = env_list("SOURCE_SITE_FALLBACK_HOSTS", "")
OTP_TOTP_ISSUER = env("OTP_TOTP_ISSUER", "RSalehin24 Library")
CATALOG_EXPORT_FONT_PATH = env("CATALOG_EXPORT_FONT_PATH", "")


INSTALLED_APPS = [
    "apps.accounts.admin_apps.MaintenanceAdminConfig",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "anymail",
    "corsheaders",
    "rest_framework",
    "drf_spectacular",
    "django_filters",
    "django_otp",
    "django_otp.plugins.otp_totp",
    "apps.common",
    "apps.accounts",
    "apps.catalog",
    "apps.ingestion",
    "apps.processing",
    "apps.access",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "apps.common.middleware.RequireTotpSetupMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": {
        **database_config(
            env(
                "DATABASE_URL",
                "postgresql://postgres:postgres@postgres:5432/bangla_library",
            )
        ),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": True,
    }
}
REDIS_CACHE_URL = env("REDIS_CACHE_URL", "redis://redis:6379/1")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache"
        if APP_ENV == "production"
        else "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": REDIS_CACHE_URL
        if APP_ENV == "production"
        else "elibrary-development",
        "OPTIONS": {
            "socket_connect_timeout": 2,
            "socket_timeout": 2,
            "max_connections": 32,
        }
        if APP_ENV == "production"
        else {},
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("TIME_ZONE", "Asia/Dhaka")

USE_I18N = True
USE_TZ = True

REST_FRAMEWORK = rest_framework_settings(env)
SPECTACULAR_SETTINGS = api_schema_settings()
CSRF_FAILURE_VIEW = "apps.common.csrf.csrf_failure"

STATIC_URL = "/static/"
RUNTIME_STORAGE_DIR = Path(env("RUNTIME_STORAGE_DIR", str(BASE_DIR / "storage")))
# Auth cookie state file lives in the runtime storage dir so it always tracks the
# mounted storage volume. An explicit SOURCE_SITE_AUTH_STATE_PATH still overrides it.
SOURCE_SITE_AUTH_STATE_PATH = env("SOURCE_SITE_AUTH_STATE_PATH", "") or str(
    RUNTIME_STORAGE_DIR / "source_site_auth.json"
)
STATIC_ROOT = Path(env("STATIC_ROOT", str(RUNTIME_STORAGE_DIR / "staticfiles")))
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(RUNTIME_STORAGE_DIR / "media")))
PROTECTED_FILES_USE_NGINX = env_bool(
    "PROTECTED_FILES_USE_NGINX", APP_ENV == "production"
)
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750

public_urls_use_https = any(
    origin.startswith("https://") for origin in {FRONTEND_BASE_URL, PUBLIC_API_ORIGIN}
)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", public_urls_use_https)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", public_urls_use_https)
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", APP_ENV == "production")
SECURE_HSTS_SECONDS = env_int(
    "DJANGO_SECURE_HSTS_SECONDS", 31536000 if APP_ENV == "production" else 0
)
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
USE_X_FORWARDED_HOST = env_bool("DJANGO_USE_X_FORWARDED_HOST", True)

if env_bool("DJANGO_SECURE_PROXY_SSL_HEADER", True):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", "redis://redis:6379/0")
PROCESSING_CHECKPOINT_REDIS_URL = env(
    "PROCESSING_CHECKPOINT_REDIS_URL",
    CELERY_RESULT_BACKEND,
)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", APP_ENV != "production")
CELERY_TASK_EAGER_PROPAGATES = True
# RabbitMQ 4.3 rejects transient non-exclusive control and event queues.
CELERY_CONTROL_QUEUE_DURABLE = True
CELERY_EVENT_QUEUE_EXCLUSIVE = True
BACKGROUND_JOB_SOFT_TIMEOUT_SECONDS, KINDLE_MAX_ATTACHMENT_BYTES = background_limits(
    env_int
)
BACKGROUND_PROCESSING_QUEUE = processing_queue_name(
    env("BACKGROUND_PROCESSING_QUEUE", "processing")
)
PROCESSING_USE_LIVE_SYNC = env_bool("PROCESSING_USE_LIVE_SYNC", True)
PROCESSING_INLINE_PIPELINE_ADVANCE = env_bool(
    "PROCESSING_INLINE_PIPELINE_ADVANCE", False
)
CELERY_PROCESSING_CONCURRENCY = int(env("CELERY_PROCESSING_CONCURRENCY", "1"))

BREVO_API_KEY = env("BREVO_API_KEY", "")
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "anymail.backends.brevo.EmailBackend"
    if BREVO_API_KEY
    else "django.core.mail.backends.console.EmailBackend",
)
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = env_bool("EMAIL_USE_SSL", False)
EMAIL_TIMEOUT = int(env("EMAIL_TIMEOUT", "20"))
BREVO_SENDER_EMAIL = env("BREVO_SENDER_EMAIL", "")
ACCOUNT_INVITE_FROM_EMAIL = env(
    "ACCOUNT_INVITE_FROM_EMAIL",
    BREVO_SENDER_EMAIL or DEFAULT_FROM_EMAIL,
)
ANYMAIL = {
    "BREVO_API_KEY": BREVO_API_KEY,
    "SEND_DEFAULTS": {
        "from_email": ACCOUNT_INVITE_FROM_EMAIL,
    },
}

LOGGING = logging_settings(env("LOG_LEVEL", "INFO"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

validate_production_settings(
    {
        "APP_ENV": APP_ENV,
        "DEBUG": DEBUG,
        "SECRET_KEY": SECRET_KEY,
        "CELERY_TASK_ALWAYS_EAGER": CELERY_TASK_ALWAYS_EAGER,
        "SESSION_COOKIE_SECURE": SESSION_COOKIE_SECURE,
        "CSRF_COOKIE_SECURE": CSRF_COOKIE_SECURE,
        "SECURE_SSL_REDIRECT": SECURE_SSL_REDIRECT,
        "LEGACY_API_ENABLED": LEGACY_API_ENABLED,
        "ALLOWED_HOSTS": ALLOWED_HOSTS,
        "PUBLIC_BASE_URL": PUBLIC_BASE_URL,
        "PUBLIC_API_ORIGIN": PUBLIC_API_ORIGIN,
        "FRONTEND_BASE_URL": FRONTEND_BASE_URL,
        "DATABASES": DATABASES,
        "CELERY_BROKER_URL": CELERY_BROKER_URL,
        "LEGACY_ENGINE_ENABLED": LEGACY_ENGINE_ENABLED,
        "REDIS_CACHE_URL": REDIS_CACHE_URL,
    }
)
