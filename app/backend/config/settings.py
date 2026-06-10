import os
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent.parent


def env(key, default=None):
    return os.environ.get(key, default)


def env_bool(key, default=False):
    value = env(key)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key, default=0):
    value = env(key)
    if value is None or str(value).strip() == "":
        return default
    return int(value)


def env_list(key, default=""):
    raw_value = env(key, default)
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def append_unique(items, value):
    if value and value not in items:
        items.append(value)
    return items


def normalized_origin(value):
    parsed = urlparse((value or "").strip())
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def hostname_from_url(value):
    parsed = urlparse((value or "").strip())
    return parsed.hostname or ""


def database_config(url):
    parsed = urlparse(url)
    engine_map = {
        "postgres": "django.db.backends.postgresql",
        "postgresql": "django.db.backends.postgresql",
        "pgsql": "django.db.backends.postgresql",
    }
    engine = engine_map.get(parsed.scheme)
    if not engine:
        raise ValueError(f"Unsupported database scheme: {parsed.scheme}")

    return {
        "ENGINE": engine,
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": parsed.port or "",
    }


APP_ENV = env("APP_ENV", "development")
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

for host in {hostname_from_url(FRONTEND_BASE_URL), hostname_from_url(PUBLIC_API_ORIGIN)}:
    append_unique(ALLOWED_HOSTS, host)

for origin in {normalized_origin(FRONTEND_BASE_URL), normalized_origin(PUBLIC_API_ORIGIN)}:
    append_unique(CSRF_TRUSTED_ORIGINS, origin)
    append_unique(CORS_ALLOWED_ORIGINS, origin)

if DEBUG:
    for host in ("localhost", "127.0.0.1"):
        for port in range(5173, 5182):
            origin = f"http://{host}:{port}"
            append_unique(CSRF_TRUSTED_ORIGINS, origin)
            append_unique(CORS_ALLOWED_ORIGINS, origin)

PASSWORD_CREATE_FRONTEND_PATH = env(
    "PASSWORD_CREATE_FRONTEND_PATH", "/create-password"
)
PASSWORD_RESET_FRONTEND_PATH = env(
    "PASSWORD_RESET_FRONTEND_PATH", "/reset-password/confirm"
)
PASSWORD_RESET_TIMEOUT = env_int("PASSWORD_RESET_TIMEOUT", 6 * 60 * 60)
SUPER_ADMIN_EMAIL = env("SUPER_ADMIN_EMAIL", "library@rsalehin24.me")
SUPER_ADMIN_PASSWORD = env("SUPER_ADMIN_PASSWORD", "")
SOURCE_SITE_EMAIL = env("SOURCE_SITE_EMAIL", "")
SOURCE_SITE_PASSWORD = env("SOURCE_SITE_PASSWORD", "")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "RSalehin24 Library <library@rsalehin24.me>")
SOURCE_SITE_HOST = env("SOURCE_SITE_HOST", "").strip().lower()
SOURCE_SITE_FALLBACK_HOSTS = env_list("SOURCE_SITE_FALLBACK_HOSTS", "")
OTP_TOTP_ISSUER = env("OTP_TOTP_ISSUER", "RSalehin24 Library")
CATALOG_EXPORT_FONT_PATH = env("CATALOG_EXPORT_FONT_PATH", "")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "anymail",
    "corsheaders",
    "rest_framework",
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
            env("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/bangla_library")
        ),
        "CONN_MAX_AGE": env_int("DB_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": True,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
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

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "login": env("THROTTLE_LOGIN", "10/hour"),
        "register": env("THROTTLE_REGISTER", "5/hour"),
        "password_reset": env("THROTTLE_PASSWORD_RESET", "5/hour"),
        "submission": env("THROTTLE_SUBMISSION", "40/hour"),
    },
}

STATIC_URL = "/static/"
RUNTIME_STORAGE_DIR = Path(env("RUNTIME_STORAGE_DIR", str(BASE_DIR / "storage")))
# Auth cookie state file lives in the runtime storage dir so it always tracks the
# mounted storage volume. An explicit SOURCE_SITE_AUTH_STATE_PATH still overrides it.
SOURCE_SITE_AUTH_STATE_PATH = env("SOURCE_SITE_AUTH_STATE_PATH", "") or str(RUNTIME_STORAGE_DIR / "source_site_auth.json")
STATIC_ROOT = Path(env("STATIC_ROOT", str(RUNTIME_STORAGE_DIR / "staticfiles")))
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(RUNTIME_STORAGE_DIR / "media")))

public_urls_use_https = any(origin.startswith("https://") for origin in {FRONTEND_BASE_URL, PUBLIC_API_ORIGIN})

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = env("SESSION_COOKIE_SAMESITE", "Lax")
SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", public_urls_use_https)
CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", public_urls_use_https)
CSRF_COOKIE_SAMESITE = env("CSRF_COOKIE_SAMESITE", "Lax")
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
USE_X_FORWARDED_HOST = env_bool("DJANGO_USE_X_FORWARDED_HOST", True)

if env_bool("DJANGO_SECURE_PROXY_SSL_HEADER", True):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://redis:6379/0")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)
PROCESSING_CHECKPOINT_REDIS_URL = env(
    "PROCESSING_CHECKPOINT_REDIS_URL",
    CELERY_BROKER_URL,
)
CELERY_TASK_ALWAYS_EAGER = env_bool("CELERY_TASK_ALWAYS_EAGER", APP_ENV != "production")
CELERY_TASK_EAGER_PROPAGATES = True
PROCESSING_USE_LIVE_SYNC = env_bool("PROCESSING_USE_LIVE_SYNC", True)
PROCESSING_INLINE_PIPELINE_ADVANCE = env_bool("PROCESSING_INLINE_PIPELINE_ADVANCE", False)

BREVO_API_KEY = env("BREVO_API_KEY", "")
EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    "anymail.backends.brevo.EmailBackend" if BREVO_API_KEY else "django.core.mail.backends.console.EmailBackend",
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

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "structured",
        }
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", "INFO"),
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
