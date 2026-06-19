from django.apps import AppConfig


class IngestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ingestion'
    label = 'ingestion'
    verbose_name = 'Ingestion'

    def ready(self):
        import apps.ingestion.signals  # noqa: F401
