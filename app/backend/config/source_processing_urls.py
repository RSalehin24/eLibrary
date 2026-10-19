from apps.ingestion.catalog_processing.api import CatalogProcessingView
from apps.ingestion.source_discovery.api import SourceDiscoveryView
from apps.ingestion.source_processing.api import ProcessSourceView, SourceIssueView
from apps.ingestion.source_processing.bulk import ProcessSourceSelectionView
from apps.processing.bulk_control_api import BulkJobControlView
from django.urls import path

urlpatterns = [
    path(
        "manage/jobs/bulk-control/",
        BulkJobControlView.as_view(),
        name="managed-jobs-bulk-control",
    ),
    path(
        "manage/sources/process-all/",
        CatalogProcessingView.as_view(),
        name="process-all-catalog",
    ),
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
