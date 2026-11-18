from django.urls import path

from apps.common.views import CsrfCookieView, HealthCheckView, SavedFilterDetailView, SavedFilterListCreateView


urlpatterns = [
    path("health/", HealthCheckView.as_view(), name="health-check"),
    path("csrf/", CsrfCookieView.as_view(), name="csrf-cookie"),
    path("saved-filters/", SavedFilterListCreateView.as_view(), name="saved-filter-list"),
    path("saved-filters/<uuid:pk>/", SavedFilterDetailView.as_view(), name="saved-filter-detail"),
]
