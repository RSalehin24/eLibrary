from collections.abc import Callable


def api_schema_settings() -> dict[str, object]:
    return {
        "TITLE": "Bengali Library API",
        "VERSION": "1.0.0",
        "COMPONENT_SPLIT_PATCH": False,
        "ENUM_NAME_OVERRIDES": {
            "HighlightKindEnum": "apps.access.models.HighlightKind.choices",
            "BackgroundJobStateEnum": "apps.processing.job_models.BackgroundJobState.choices",
            "BackgroundJobKindEnum": "apps.processing.job_models.BackgroundJobKind.choices",
            "LifecycleStateEnum": "apps.common.models.LifecycleState.choices",
            "JobControlActionEnum": "apps.processing.job_serializers.JOB_CONTROL_ACTIONS",
            "BulkJobControlActionEnum": "apps.processing.bulk_control_serializers.BULK_JOB_CONTROL_ACTIONS",
        },
    }


def rest_framework_settings(environment: Callable) -> dict[str, object]:
    return {
        "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "rest_framework.authentication.SessionAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
        "DEFAULT_FILTER_BACKENDS": [
            "django_filters.rest_framework.DjangoFilterBackend",
        ],
        "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
        "DEFAULT_THROTTLE_RATES": {
            "login": environment("THROTTLE_LOGIN", "10/hour"),
            "register": environment("THROTTLE_REGISTER", "5/hour"),
            "password_reset": environment("THROTTLE_PASSWORD_RESET", "5/hour"),
            "password_link": environment("THROTTLE_PASSWORD_LINK", "20/hour"),
            "submission": environment("THROTTLE_SUBMISSION", "40/hour"),
        },
    }
