from django.db.models import Count, Min, Q
from django.db.models.functions import Coalesce
from django.urls import reverse
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.accounts.link_mail.queries import invitation_jobs
from apps.accounts.management_access.policy import editable_accounts
from apps.accounts.models import User
from apps.accounts.workspaces import management_sections
from apps.catalog.discovery.management import metadata_managed_books
from apps.common.models import LifecycleState
from apps.ingestion.source_workspace.queries import source_entries
from apps.processing.job_models import (
    BackgroundJob,
    BackgroundJobKind,
    BackgroundJobState,
)

ISSUE_LIMIT = 5
ISSUE_STATES = (BackgroundJobState.FAILED, BackgroundJobState.NEEDS_ATTENTION)


def require_overview(actor):
    sections = management_sections(actor)
    if "overview" not in sections:
        raise PermissionDenied("A management workspace is required.")
    return sections


def work_counts(jobs):
    now = timezone.now()
    counts = jobs.aggregate(
        queued=Count("id", filter=Q(state="queued")),
        running=Count("id", filter=Q(state="running")),
        retry_wait=Count("id", filter=Q(state="retry_wait")),
        paused=Count("id", filter=Q(state="paused")),
        failed=Count("id", filter=Q(state="failed")),
        needs_attention=Count("id", filter=Q(state="needs_attention")),
        oldest_waiting_at=Min(
            "available_at",
            filter=Q(state__in=["queued", "retry_wait"], available_at__lte=now),
        ),
    )
    oldest = counts.pop("oldest_waiting_at")
    counts["oldest_wait_seconds"] = (
        max(0, int((now - oldest).total_seconds())) if oldest else None
    )
    return counts


def issue_summary(job):
    mail = job.kind == BackgroundJobKind.ACCOUNT_MAIL
    route = "account-mail-operation" if mail else "managed-job-detail"
    return {
        "id": job.pk,
        "kind": job.kind,
        "state": job.state,
        "title": "পাঠকের আমন্ত্রণ"
        if mail
        else (
            job.book.title
            if job.book
            else job.source_record.title
            if job.source_record
            else job.get_kind_display()
        ),
        "error_code": job.error_code,
        "finished_at": job.finished_at,
        "status_url": reverse(f"api_v1:{route}", kwargs={"identifier": job.pk}),
    }


def work_summary(jobs):
    recent = (
        jobs.filter(state__in=ISSUE_STATES)
        .select_related("book", "source_record")
        .only(
            "id",
            "kind",
            "state",
            "book__title",
            "source_record__title",
            "error_code",
            "finished_at",
        )
        .annotate(issue_at=Coalesce("finished_at", "updated_at"))
        .order_by("-issue_at", "-id")[:ISSUE_LIMIT]
    )
    return {
        "counts": work_counts(jobs),
        "issues": [issue_summary(job) for job in recent],
    }


def work_for_sections(actor, sections):
    processing = BackgroundJob.objects.exclude(kind=BackgroundJobKind.ACCOUNT_MAIL)
    mail = (
        invitation_jobs().filter(account__in=editable_accounts(actor))
        if "users-access" in sections
        else None
    )
    return {
        "generated_at": timezone.now(),
        "processing": work_summary(processing) if "jobs" in sections else None,
        "account_mail": work_summary(mail) if mail is not None else None,
    }


def overview_work(actor):
    return work_for_sections(actor, require_overview(actor))


def book_counts(actor):
    return (
        metadata_managed_books(actor)
        .values("id", "state", "editorial_reviewed_at")
        .aggregate(
            total=Count("id", distinct=True),
            draft=Count("id", distinct=True, filter=Q(state=LifecycleState.DRAFT)),
            published=Count(
                "id", distinct=True, filter=Q(state=LifecycleState.PUBLISHED)
            ),
            editorial_pending=Count(
                "id", distinct=True, filter=Q(editorial_reviewed_at__isnull=True)
            ),
        )
    )


def source_counts():
    counts = source_entries({"q": "", "status": "all"}).aggregate(
        total=Count("id"),
        unlinked=Count("id", filter=Q(linked=False)),
        linked_count=Count("id", filter=Q(linked=True, removed=False)),
        removed_count=Count("id", filter=Q(removed=True)),
    )
    counts["linked"] = counts.pop("linked_count")
    counts["removed"] = counts.pop("removed_count")
    return counts


def account_counts():
    return User.objects.aggregate(
        total=Count("id"),
        active=Count("id", filter=Q(is_active=True)),
        setup_pending=Count("id", filter=Q(email_setup_pending=True, is_active=True)),
    )


def management_overview(actor):
    sections = require_overview(actor)
    return {
        "generated_at": timezone.now(),
        "books": book_counts(actor) if "books" in sections else None,
        "sources": source_counts() if "sources" in sections else None,
        "accounts": account_counts() if "users-access" in sections else None,
        "work": work_for_sections(actor, sections),
    }
