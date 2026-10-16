from apps.processing.automations.api import (
    AutomationDetailView,
    AutomationListView,
    AutomationRunsView,
)
from django.urls import path

automation_routes = [
    path("manage/automations/", AutomationListView.as_view(), name="automations"),
    path(
        "manage/automations/<uuid:identifier>/",
        AutomationDetailView.as_view(),
        name="automation",
    ),
    path(
        "manage/automations/<uuid:identifier>/runs/",
        AutomationRunsView.as_view(),
        name="automation-runs",
    ),
]
