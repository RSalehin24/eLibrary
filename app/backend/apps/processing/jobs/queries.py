from django.db.models import Exists, OuterRef, Prefetch, Subquery

from apps.catalog.discovery.management import metadata_managed_books
from apps.processing.job_models import (
    SOURCE_ACTIVE_STATES,
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
    JobAttempt,
    RequestedJobAction,
)


def job_queryset(user):
    attempts = JobAttempt.objects.filter(job=OuterRef("pk")).order_by("-number")
    return (
        BackgroundJob.objects.select_related("book", "source_record")
        .exclude(kind=BackgroundJobKind.ACCOUNT_MAIL)
        .only(
            "id",
            "kind",
            "state",
            "requested_action",
            "book_id",
            "asset_id",
            "source_record_id",
            "parent_job_id",
            "checkpoint",
            "input",
            "attempt_count",
            "max_attempts",
            "error_code",
            "available_at",
            "created_at",
            "updated_at",
            "finished_at",
            "book__id",
            "book__title",
            "book__slug",
            "book__updated_at",
            "book__record_type",
            "book__state",
            "book__deleted_at",
            "source_record__id",
            "source_record__title",
            "source_record__updated_at",
        )
        .annotate(
            can_edit_book=Exists(
                metadata_managed_books(user).filter(pk=OuterRef("book_id"))
            ),
            other_book_work=Exists(
                BackgroundJob.objects.filter(
                    book_id=OuterRef("book_id"), state__in=SOURCE_ACTIVE_STATES
                ).exclude(pk=OuterRef("pk"))
            ),
            latest_stage=Subquery(attempts.values("stage")[:1]),
            latest_heartbeat_at=Subquery(attempts.values("heartbeat_at")[:1]),
        )
    )


def job_detail_queryset(user):
    attempts = JobAttempt.objects.order_by("-number")[:20]
    return job_queryset(user).prefetch_related(
        Prefetch("attempts", queryset=attempts, to_attr="recent_attempts")
    )


def available_job_actions(job):
    if job.state == BackgroundJobState.PAUSED:
        return ["resume", "cancel"]
    if job.state not in {
        BackgroundJobState.RUNNING,
        BackgroundJobState.QUEUED,
        BackgroundJobState.RETRY_WAIT,
    }:
        return []
    if job.requested_action == RequestedJobAction.CANCEL:
        return []
    return (
        ["cancel"]
        if job.requested_action == RequestedJobAction.PAUSE
        else ["pause", "cancel"]
    )
