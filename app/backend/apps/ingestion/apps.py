from django.apps import AppConfig
from django.conf import settings


class IngestionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ingestion"
    label = "ingestion"
    verbose_name = "Ingestion"

    def ready(self):
        if settings.LEGACY_ENGINE_ENABLED:
            import apps.ingestion.signals  # noqa: F401
