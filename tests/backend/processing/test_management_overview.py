from datetime import timedelta
from uuid import uuid4

import pytest
from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.link_mail.requests import request_invitation, request_password_reset
from apps.accounts.models import User
from apps.catalog.models import Book, BookSource
from apps.ingestion.models import SourceCatalogEntry
from apps.processing.job_models import BackgroundJob, BackgroundJobKind
from apps.processing.overview.queries import management_overview
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

OVERVIEW = "/api/v1/manage/overview/"
WORK = f"{OVERVIEW}work/"
pytestmark = pytest.mark.django_db


def test_readers_anonymous_and_disabled_accounts_cannot_read_overview(client):
    assert client.get(OVERVIEW).status_code == client.get(WORK).status_code == 403
    reader = User.objects.create_user(email="overview-reader@library.test")
    client.force_login(reader)
    assert client.get(OVERVIEW).status_code == client.get(WORK).status_code == 403
    reader.is_staff = True
    reader.is_active = False
    reader.save()
    assert client.get(OVERVIEW).status_code == 403


def test_scoped_editors_count_only_manageable_books_without_other_domains(client):
    editor = User.objects.create_user(email="overview-editor@library.test")
    draft = Book.objects.create(title="অনুমোদিত খসড়া")
    approved = Book.objects.create(
        title="অনুমোদিত প্রকাশনা", state="published", editorial_reviewed_at=timezone.now()
    )
    Book.objects.create(title="অন্য বই")
    removed = Book.objects.create(title="অপসারিত", deleted_at=timezone.now())
    for book in [draft, approved, removed]:
        PermissionGrant.objects.create(
            user=editor, book=book, scope=PermissionScope.METADATA_EDIT
        )
    client.force_login(editor)
    response = client.get(OVERVIEW)
    assert response.status_code == 200
    data = response.json()
    assert data["books"] == {
        "total": 2,
        "draft": 1,
        "published": 1,
        "editorial_pending": 1,
    }
    assert data["sources"] is None and data["accounts"] is None
    assert data["work"]["processing"] is None and data["work"]["account_mail"] is None
    assert (
        response["Cache-Control"] == "private, no-store"
        and response["X-Robots-Tag"] == "noindex"
    )


def test_processing_overview_measures_due_queue_age_and_lists_bounded_failures(
    client, preparation_job
):
    actor = preparation_job.requested_by
    old = timezone.now() - timedelta(minutes=10)
    BackgroundJob.objects.filter(pk=preparation_job.pk).update(
        created_at=old, available_at=old
    )
    for number in range(8):
        BackgroundJob.objects.create(
            book=preparation_job.book,
            asset=preparation_job.asset,
            requested_by=actor,
            kind=BackgroundJobKind.PREPARE_EPUB,
            state="needs_attention" if number == 0 else "failed",
            available_at=timezone.now(),
            finished_at=timezone.now(),
            error_code="fixture_failure",
            input={"token": "private-marker"},
        )
    client.force_login(actor)
    data = client.get(WORK).json()["processing"]
    assert data["counts"]["queued"] == 1 and data["counts"]["failed"] == 7
    assert data["counts"]["needs_attention"] == 1
    assert 600 <= data["counts"]["oldest_wait_seconds"] <= 610
    assert len(data["issues"]) == 5
    assert all(issue["title"] == preparation_job.book.title for issue in data["issues"])
    assert "private-marker" not in str(data)
    assert all(
        client.get(issue["status_url"]).status_code == 200 for issue in data["issues"]
    )


def test_future_retry_does_not_inflate_the_due_queue_age(client, preparation_job):
    preparation_job.state = "retry_wait"
    preparation_job.available_at = timezone.now() + timedelta(minutes=10)
    preparation_job.save()
    client.force_login(preparation_job.requested_by)
    counts = client.get(WORK).json()["processing"]["counts"]
    assert counts["retry_wait"] == 1 and counts["oldest_wait_seconds"] is None


def test_recent_failures_use_update_time_when_completion_time_is_missing(
    client, preparation_job
):
    actor = preparation_job.requested_by
    now = timezone.now()
    target = {"book": preparation_job.book, "asset": preparation_job.asset}
    for _ in range(6):
        job = BackgroundJob.objects.create(
            requested_by=actor,
            kind="prepare_epub",
            state="needs_attention",
            available_at=now,
            **target,
        )
        BackgroundJob.objects.filter(pk=job.pk).update(
            updated_at=now - timedelta(days=1)
        )
    completed = BackgroundJob.objects.create(
        requested_by=actor,
        kind="prepare_epub",
        state="failed",
        available_at=now,
        finished_at=now - timedelta(minutes=1),
        **target,
    )
    incomplete = BackgroundJob.objects.create(
        requested_by=actor,
        kind="prepare_epub",
        state="needs_attention",
        available_at=now,
        **target,
    )
    client.force_login(actor)
    issues = client.get(WORK).json()["processing"]["issues"]
    assert len(issues) == 5
    assert [issue["id"] for issue in issues[:2]] == [
        str(incomplete.pk),
        str(completed.pk),
    ]


def test_resumed_work_queue_age_starts_when_it_becomes_available(
    client, preparation_job
):
    from apps.processing.jobs.controls import resume_job

    old = timezone.now() - timedelta(days=1)
    BackgroundJob.objects.filter(pk=preparation_job.pk).update(
        state="paused", created_at=old, available_at=old
    )
    resume_job(preparation_job.pk)
    client.force_login(preparation_job.requested_by)
    counts = client.get(WORK).json()["processing"]["counts"]
    assert counts["queued"] == 1 and 0 <= counts["oldest_wait_seconds"] <= 10


def test_source_counts_use_exact_linkage_and_distinguish_removed_books(
    client, preparation_job
):
    for label in ["linked", "removed", "new"]:
        source = SourceCatalogEntry.objects.create(
            source_url=f"https://source.test/{label}/",
            title=label,
            normalized_title=label,
        )
        if label == "new":
            continue
        book = (
            preparation_job.book
            if label == "linked"
            else Book.objects.create(title=label, deleted_at=timezone.now())
        )
        BookSource.objects.create(
            book=book,
            source_url=source.source_url,
            normalized_source_url=source.source_url,
        )
    client.force_login(preparation_job.requested_by)
    assert client.get(OVERVIEW).json()["sources"] == {
        "total": 3,
        "linked": 1,
        "removed": 1,
        "unlinked": 1,
    }


def test_access_overview_excludes_reset_and_protected_account_mail(client):
    actor = User.objects.create_user(email="overview-access@library.test")
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.ACCESS_MANAGE)
    job = request_invitation(
        actor, {"operation_id": str(uuid4()), "email": "overview-invited@library.test"}
    )
    reset = User.objects.create_user(
        email="overview-reset@library.test", password="previous-password"
    )
    request_password_reset(reset.email)
    privileged = User.objects.create_superuser(
        email="overview-maintainer@library.test", password="previous-password"
    )
    protected = request_invitation(
        privileged,
        {"operation_id": str(uuid4()), "email": "overview-staff@library.test"},
    )
    protected.account.is_staff = True
    protected.account.save()
    client.force_login(actor)
    data = client.get(OVERVIEW).json()
    assert (
        data["books"] is None
        and data["sources"] is None
        and data["work"]["processing"] is None
    )
    assert (
        data["accounts"]["setup_pending"] == 2
        and data["work"]["account_mail"]["counts"]["queued"] == 1
    )
    job.state = "needs_attention"
    job.finished_at = timezone.now()
    job.save()
    issue = client.get(WORK).json()["account_mail"]["issues"][0]
    assert (
        issue["kind"] == "account_mail"
        and client.get(issue["status_url"]).status_code == 200
    )
    assert job.account.email not in str(issue)


def test_processing_only_accounts_cannot_observe_mail_counts(client, preparation_job):
    actor = preparation_job.requested_by
    actor.is_staff = False
    actor.save()
    PermissionGrant.objects.create(user=actor, scope=PermissionScope.PROCESSING_MANAGE)
    manager = User.objects.create_superuser(
        email="overview-processor-private@library.test", password="previous-password"
    )
    request_invitation(
        manager,
        {"operation_id": str(uuid4()), "email": "overview-private-invite@library.test"},
    )
    client.force_login(actor)
    data = client.get(OVERVIEW).json()
    assert data["accounts"] is None and data["work"]["account_mail"] is None
    assert data["work"]["processing"]["counts"]["queued"] == 1


def test_overview_queries_are_bounded_and_do_not_read_book_bodies_or_mail_inputs(
    preparation_job,
):
    actor = preparation_job.requested_by
    with CaptureQueriesContext(connection) as first:
        management_overview(actor)
    jobs = [
        BackgroundJob(
            book=preparation_job.book,
            asset=preparation_job.asset,
            requested_by=actor,
            kind="prepare_epub",
            state="failed",
            available_at=timezone.now(),
            finished_at=timezone.now(),
        )
        for _ in range(100)
    ]
    BackgroundJob.objects.bulk_create(jobs)
    with CaptureQueriesContext(connection) as expanded:
        data = management_overview(actor)
    assert len(expanded) == len(first) and len(expanded) <= 10
    assert len(data["work"]["processing"]["issues"]) == 5
    sql = " ".join(query["sql"] for query in expanded.captured_queries)
    assert "main_content_html" not in sql and "raw_data" not in sql
    assert all(
        '"input"' not in query["sql"].split(" FROM ", 1)[0]
        for query in expanded.captured_queries
    )


def test_revoked_scoped_editor_loses_overview_access(client):
    actor = User.objects.create_user(email="overview-revocation@library.test")
    book = Book.objects.create(title="সীমিত অনুমতির বই")
    grant = PermissionGrant.objects.create(
        user=actor, book=book, scope=PermissionScope.METADATA_EDIT
    )
    client.force_login(actor)
    assert client.get(OVERVIEW).status_code == 200
    grant.is_active = False
    grant.save()
    assert client.get(OVERVIEW).status_code == client.get(WORK).status_code == 403
