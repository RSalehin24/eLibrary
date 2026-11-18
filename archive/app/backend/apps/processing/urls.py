from django.urls import path

from .views import (
    ProcessingCardView,
    ProcessingCatalogAutomationRunView,
    ProcessingCatalogAutomationView,
    ProcessingIncompleteAutomationRunView,
    ProcessingIncompleteAutomationView,
    ProcessingRecordCreateRequestsView,
    ProcessingRequestActionView,
    ProcessingTableView,
    ProcessingStateView,
    ProcessingSyncPauseView,
    ProcessingSyncResumeView,
    ProcessingSyncStopView,
    ProcessingSyncStartView,
    ProcessingStreamView,
)


urlpatterns = [
    path("state/", ProcessingStateView.as_view(), name="processing-state"),
    path("card/", ProcessingCardView.as_view(), name="processing-card"),
    path("table/", ProcessingTableView.as_view(), name="processing-table"),
    path("stream/", ProcessingStreamView.as_view(), name="processing-stream"),
    path("sync/start/", ProcessingSyncStartView.as_view(), name="processing-sync-start"),
    path("sync/pause/", ProcessingSyncPauseView.as_view(), name="processing-sync-pause"),
    path("sync/resume/", ProcessingSyncResumeView.as_view(), name="processing-sync-resume"),
    path("sync/stop/", ProcessingSyncStopView.as_view(), name="processing-sync-stop"),
    path("sync/<slug:scope>/pause/", ProcessingSyncPauseView.as_view(), name="processing-sync-scope-pause"),
    path("sync/<slug:scope>/resume/", ProcessingSyncResumeView.as_view(), name="processing-sync-scope-resume"),
    path("sync/<slug:scope>/stop/", ProcessingSyncStopView.as_view(), name="processing-sync-scope-stop"),
    path("records/create-requests/", ProcessingRecordCreateRequestsView.as_view(), name="processing-record-create-requests"),
    path("requests/action/", ProcessingRequestActionView.as_view(), name="processing-request-action"),
    path("automation/catalog/", ProcessingCatalogAutomationView.as_view(), name="processing-catalog-automation"),
    path("automation/catalog/run/", ProcessingCatalogAutomationRunView.as_view(), name="processing-catalog-automation-run"),
    path("automation/incomplete/", ProcessingIncompleteAutomationView.as_view(), name="processing-incomplete-automation"),
    path("automation/incomplete/run/", ProcessingIncompleteAutomationRunView.as_view(), name="processing-incomplete-automation-run"),
]
