from apps.ingestion.models import (
    BookSubmission,
    CatalogCurationRun,
    JobStatus,
    ProcessingJob,
    SourceCatalogRefreshState,
    SubmissionOrigin,
    SubmissionStatus,
)
from apps.ingestion.services.curation import (
    ACTIVE_RUN_STATUSES,
    ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES,
)
from apps.ingestion.services.submissions import can_manage_processing_records

ACTIVE_SUBMISSION_STATUSES = (
    SubmissionStatus.PENDING_RESOLUTION,
    SubmissionStatus.QUEUED,
    SubmissionStatus.PROCESSING,
)
ACTIVE_JOB_STATUSES = (JobStatus.QUEUED, JobStatus.PROCESSING)


def get_processing_activity_snapshot(user):
    can_manage = can_manage_processing_records(user)
    active_scopes = []

    visible_submissions = BookSubmission.objects.all()
    visible_jobs = ProcessingJob.objects.select_related("submission")
    if not can_manage:
        visible_submissions = visible_submissions.filter(submitter=user)
        visible_jobs = visible_jobs.filter(submission__submitter=user)

    if visible_submissions.filter(status__in=ACTIVE_SUBMISSION_STATUSES).exists():
        active_scopes.append("submissions")

    if visible_jobs.filter(status__in=ACTIVE_JOB_STATUSES).exists():
        active_scopes.append("jobs")

    if can_manage:
        if visible_jobs.filter(
            submission__origin=SubmissionOrigin.CURATION,
            status__in=ACTIVE_JOB_STATUSES,
        ).exists():
            active_scopes.append("source_jobs")

        if visible_jobs.filter(
            submission__origin=SubmissionOrigin.AUTOMATION,
            status__in=ACTIVE_JOB_STATUSES,
        ).exists():
            active_scopes.append("automation_jobs")

        if CatalogCurationRun.objects.filter(status__in=ACTIVE_RUN_STATUSES).exists():
            active_scopes.append("runs")

        if SourceCatalogRefreshState.objects.filter(
            singleton_key="default",
            status__in=ACTIVE_SOURCE_CATALOG_REFRESH_STATUSES,
        ).exists():
            active_scopes.append("catalog_refresh")

    return {
        "can_manage_processing": can_manage,
        "has_visible_activity": bool(active_scopes),
        "active_scopes": active_scopes,
    }


__all__ = ["get_processing_activity_snapshot"]
