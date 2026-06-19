from apps.ingestion.services.curation import create_catalog_curation_run
from apps.ingestion.services.submissions import create_submission_records, queue_submission

from .activity import ProcessingActivityView
from .catalog_entries import (
    SourceCatalogEntryBulkDeleteView,
    SourceCatalogEntryCreateBooksView,
    SourceCatalogEntryDetailView,
    SourceCatalogEntryListView,
)
from .curation import (
    CatalogAutomationSettingsView,
    CatalogCurationRunBulkDeleteView,
    CatalogCurationRunBulkStopView,
    CatalogCurationRunDetailView,
    CatalogCurationRunListCreateView,
    CatalogCurationRunStopView,
    SourceCatalogRefreshStopView,
    SourceCatalogRefreshView,
)
from .duplicates import DuplicateReviewListView, DuplicateReviewResolveView
from .incomplete_checks import IncompleteCatalogCheckCreateBooksView, IncompleteCatalogCheckListView
from .job_actions import (
    ProcessingJobBulkDeleteView,
    ProcessingJobBulkResumeView,
    ProcessingJobBulkStopView,
    ProcessingJobResumeView,
    ProcessingJobStopView,
)
from .jobs import ProcessingJobDetailView, ProcessingJobListView, ProcessingJobLogsView, ProcessingJobRecoverView, ProcessingJobStreamView, ReprocessJobSummaryView
from .submissions import (
    SubmissionActionLinksView,
    SubmissionBulkDeleteView,
    SubmissionBulkRetryView,
    SubmissionBulkStatusView,
    SubmissionConfirmCandidateView,
    SubmissionDetailView,
    SubmissionListCreateView,
    SubmissionRetryView,
)

__all__ = [
    "CatalogAutomationSettingsView",
    "CatalogCurationRunBulkDeleteView",
    "CatalogCurationRunBulkStopView",
    "CatalogCurationRunDetailView",
    "CatalogCurationRunListCreateView",
    "CatalogCurationRunStopView",
    "create_catalog_curation_run",
    "create_submission_records",
    "DuplicateReviewListView",
    "DuplicateReviewResolveView",
    "IncompleteCatalogCheckCreateBooksView",
    "IncompleteCatalogCheckListView",
    "ProcessingActivityView",
    "ProcessingJobBulkDeleteView",
    "ProcessingJobBulkResumeView",
    "ProcessingJobBulkStopView",
    "ProcessingJobDetailView",
    "ProcessingJobListView",
    "ProcessingJobLogsView",
    "ProcessingJobRecoverView",
    "ProcessingJobStreamView",
    "ReprocessJobSummaryView",
    "ProcessingJobResumeView",
    "ProcessingJobStopView",
    "SourceCatalogEntryBulkDeleteView",
    "SourceCatalogEntryCreateBooksView",
    "SourceCatalogEntryDetailView",
    "SourceCatalogEntryListView",
    "SourceCatalogRefreshStopView",
    "SourceCatalogRefreshView",
    "queue_submission",
    "SubmissionActionLinksView",
    "SubmissionBulkDeleteView",
    "SubmissionBulkRetryView",
    "SubmissionBulkStatusView",
    "SubmissionConfirmCandidateView",
    "SubmissionDetailView",
    "SubmissionListCreateView",
    "SubmissionRetryView",
]
