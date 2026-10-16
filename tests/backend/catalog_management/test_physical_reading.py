import pytest
from apps.accounts.models import User
from apps.catalog.models import Book, PhysicalReadingLog
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def physical_fixture():
    user = User.objects.create_user(email="paper-reader@library.test")
    client = APIClient()
    client.force_authenticate(user)
    book = Book.objects.create(
        title="কাগজের বই",
        record_type="manual",
        state="published",
        review_state="approved",
    )
    return user, client, book


def log_fields():
    return {
        "expected_updated_at": None,
        "status": "reading",
        "current_page": 25,
        "total_pages": 100,
        "rating": 4,
        "started_on": "2026-10-01",
        "finished_on": None,
        "notes": "আমার ব্যক্তিগত নোট",
    }


def test_physical_log_is_persisted_private_revision_checked_and_in_recent_feed():
    actor, client, book = physical_fixture()
    path = f"/api/v1/me/books/{book.slug}/physical-log/"
    assert client.get(path).json()["updated_at"] is None
    saved = client.put(path, log_fields(), format="json")
    assert saved.status_code == 200 and saved.json()["notes"] == log_fields()["notes"]
    assert client.put(path, log_fields(), format="json").status_code == 409
    recent = client.get("/api/v1/me/books/?view=recent").json()["entries"]
    assert len(recent) == 1 and recent[0]["progress_percent"] == 25
    client.force_authenticate(
        User.objects.create_user(email="paper-stranger@library.test")
    )
    assert client.get(path).json()["notes"] == ""
    assert PhysicalReadingLog.objects.count() == 1
    client.force_authenticate(actor)
    assert client.get(path).json() == saved.json()


@pytest.mark.parametrize(
    "changes,field",
    [
        ({"current_page": 101}, "current_page"),
        ({"total_pages": 0}, "total_pages"),
        ({"rating": 6}, "rating"),
        ({"finished_on": "2026-09-30"}, "finished_on"),
        ({"user": 1}, "user"),
    ],
)
def test_invalid_paper_logs_are_atomic(changes, field):
    _, client, book = physical_fixture()
    response = client.put(
        f"/api/v1/me/books/{book.slug}/physical-log/",
        {**log_fields(), **changes},
        format="json",
    )
    assert response.status_code == 400 and field in response.json()["field_errors"]
    assert not PhysicalReadingLog.objects.exists()


def test_digital_books_do_not_receive_physical_logs_and_paper_books_have_no_epub_actions():
    _, client, book = physical_fixture()
    assert client.get(f"/api/v1/reading/books/{book.slug}/access/").json() == {
        "can_read": False,
        "can_download": False,
        "prepared": False,
        "can_send_kindle": False,
        "active_session_id": None,
    }
    book.record_type = "digital"
    book.save()
    assert (
        client.put(
            f"/api/v1/me/books/{book.slug}/physical-log/", log_fields(), format="json"
        ).status_code
        == 400
    )
