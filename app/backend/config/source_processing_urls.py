from apps.ingestion.source_discovery.api import SourceDiscoveryView
from apps.ingestion.source_processing.api import ProcessSourceView, SourceIssueView
from apps.ingestion.source_processing.bulk import ProcessSourceSelectionView
from django.urls import path

urlpatterns = [
    path(
        "manage/sources/discovery/",
        SourceDiscoveryView.as_view(),
        name="source-discovery",
    ),
    path(
        "manage/sources/process-selection/",
        ProcessSourceSelectionView.as_view(),
        name="process-source-selection",
    ),
    path(
        "manage/sources/<uuid:identifier>/process/",
        ProcessSourceView.as_view(),
        name="process-source",
    ),
    path(
        "manage/jobs/<uuid:identifier>/source-issue/",
        SourceIssueView.as_view(),
        name="source-issue",
    ),
]
