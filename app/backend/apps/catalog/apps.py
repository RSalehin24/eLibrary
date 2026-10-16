from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.catalog'
    label = 'catalog'
    verbose_name = 'Catalog'

    def ready(self):
        from apps.catalog.signals import register_slug_history

        register_slug_history()
