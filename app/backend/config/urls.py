from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

legacy_api_patterns = [
    path("api/", include("apps.common.urls")),
    path("api/auth/", include("apps.accounts.urls")),
    path("api/catalog/", include("apps.catalog.urls")),
    path("api/ingestion/", include("apps.ingestion.urls")),
    path("api/processing/", include("apps.processing.urls")),
    path("api/access/", include("apps.access.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("config.api_v1")),
]
if settings.LEGACY_API_ENABLED:
    urlpatterns += legacy_api_patterns

if settings.DEBUG:
    urlpatterns += static(
        f"{settings.MEDIA_URL}profile-images/",
        document_root=settings.MEDIA_ROOT / "profile-images",
    )
