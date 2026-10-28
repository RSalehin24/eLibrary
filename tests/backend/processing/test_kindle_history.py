from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    BookSeries,
    Category,
    Contributor,
    GeneratedAsset,
    Series,
)
from apps.processing.job_models import BackgroundJob
from django.utils import timezone
from test_kindle_api import kindle_reader

__all__ = ["kindle_reader"]
pytestmark = pytest.mark.django_db
HISTORY = "/api/v1/me/kindle/"


def delivery(user, book, **options):
    asset, _ = GeneratedAsset.objects.get_or_create(book=book, asset_type="epub")
    job = BackgroundJob.objects.create(
        requested_by=user,
        book=book,
        asset=asset,
        kind="deliver_kindle",
        state=options.get("state", "succeeded"),
        available_at=timezone.now(),
        input={"recipients": ["reader@kindle.com"]},
    )
    if created_at := options.get("created_at"):
        BackgroundJob.objects.filter(pk=job.pk).update(created_at=created_at)
    return job


def test_combined_filters_match_writer_category_series_and_title(kindle_reader):
    client, user, asset_job = kindle_reader
    book = asset_job.book
    writer = Contributor.objects.create(name="কিন্ডল লেখক")
    translator = Contributor.objects.create(name="কিন্ডল অনুবাদক")
    category = Category.objects.create(name="কিন্ডল বিভাগ")
    series = Series.objects.create(name="কিন্ডল সিরিজ")
    BookContributor.objects.create(book=book, contributor=writer, role="author")
    BookContributor.objects.create(book=book, contributor=translator, role="translator")
    BookCategory.objects.create(book=book, category=category)
    BookSeries.objects.create(book=book, series=series)
    job = delivery(user, book)
    delivery(user, Book.objects.create(title="অন্য বই"))
    parameters = {
        "q": book.title,
        "contributor": writer.name,
        "category": category.slug,
        "series": series.name,
        "state": "succeeded",
        "sort": "title",
    }
    response = client.get(HISTORY, parameters)
    assert response.status_code == 200
    assert [entry["id"] for entry in response.data["entries"]] == [str(job.pk)]
    assert (
        client.get(HISTORY, {**parameters, "contributor": translator.name}).data[
            "entries"
        ]
        == []
    )
    assert (
        client.get(HISTORY, {**parameters, "record_type": "manual"}).status_code == 400
    )


@pytest.mark.parametrize(
    "sort", ["-sent_at", "sent_at", "-created_at", "created_at", "title", "-title"]
)
def test_sorting_is_stable_across_cursors_with_equal_values(kindle_reader, sort):
    client, user, _ = kindle_reader
    timestamps = [
        datetime(2026, 10, day, tzinfo=ZoneInfo("UTC")) for day in (10, 11, 12)
    ]
    jobs = []
    for index, title in enumerate(("Beta", "Alpha", "Alpha")):
        book = Book.objects.create(title=title)
        Book.objects.filter(pk=book.pk).update(created_at=timestamps[2 - index])
        book.refresh_from_db()
        job = delivery(
            user,
            book,
            created_at=timestamps[index] if "sent_at" in sort else timestamps[0],
        )
        job.refresh_from_db()
        jobs.append(job)
    value = (
        (lambda job: job.book.normalized_title)
        if "title" in sort
        else (lambda job: job.book.created_at)
        if "created_at" in sort
        else (lambda job: job.created_at)
    )
    expected = [
        str(job.pk)
        for job in sorted(
            jobs, key=lambda job: (value(job), job.pk), reverse=sort.startswith("-")
        )
    ]
    entries, cursor = [], ""
    for _ in jobs:
        response = client.get(HISTORY, {"sort": sort, "limit": 1, "cursor": cursor})
        assert response.status_code == 200
        entries.extend(entry["id"] for entry in response.data["entries"])
        cursor = response.data["next_cursor"]
    assert entries == expected and cursor is None


def test_history_filters_keep_private_past_books_and_enforce_account_bound_cursors(
    kindle_reader,
):
    client, user, asset_job = kindle_reader
    for _ in range(3):
        delivery(user, asset_job.book, state="failed")
    response = client.get(HISTORY, {"state": "failed", "limit": 1, "sort": "title"})
    assert response.status_code == 200 and response.data["next_cursor"]
    cursor = response.data["next_cursor"]
    assert (
        client.get(
            HISTORY, {"state": "cancelled", "cursor": cursor, "sort": "title"}
        ).status_code
        == 400
    )
    other = User.objects.create_user(email="kindle-history-other@library.test")
    client.force_authenticate(other)
    assert (
        client.get(
            HISTORY, {"state": "failed", "cursor": cursor, "sort": "title"}
        ).status_code
        == 400
    )
    assert client.get(HISTORY, {"sort": "title"}).data["entries"] == []


def test_date_filters_include_exact_dhaka_day_boundaries(kindle_reader):
    client, user, asset_job = kindle_reader
    timestamps = [
        "2026-10-17T17:59:59+00:00",
        "2026-10-17T18:00:00+00:00",
        "2026-10-18T17:59:59+00:00",
        "2026-10-18T18:00:00+00:00",
    ]
    jobs = [
        delivery(user, asset_job.book, created_at=datetime.fromisoformat(value))
        for value in timestamps
    ]
    response = client.get(
        HISTORY, {"from_date": "2026-10-18", "to_date": "2026-10-18", "sort": "sent_at"}
    )
    assert response.status_code == 200
    assert [entry["id"] for entry in response.data["entries"]] == [
        str(job.pk) for job in jobs[1:3]
    ]
    assert client.get(HISTORY, {"to_date": "9999-12-31"}).status_code == 200


@pytest.mark.parametrize(
    "parameters",
    [
        {"sort": "__proto__"},
        {"state": "unknown"},
        {"record_type": "other"},
        {"from_date": "not-a-date"},
        {"from_date": "2026-10-20", "to_date": "2026-10-18"},
        {"q": "a" * 121},
    ],
)
def test_invalid_history_filters_have_field_errors(kindle_reader, parameters):
    response = kindle_reader[0].get(HISTORY, parameters)
    assert response.status_code == 400 and response.data["field_errors"]


def test_filter_only_status_does_not_remove_books_without_writer_metadata(
    kindle_reader,
):
    client, user, asset_job = kindle_reader
    job = delivery(user, asset_job.book, state="cancelled")
    response = client.get(HISTORY, {"state": "cancelled"})
    assert response.status_code == 200
    assert [entry["id"] for entry in response.data["entries"]] == [str(job.pk)]
