import pytest

from apps.accounts.models import User
from apps.catalog.models import Book, UserBook
from apps.ingestion.models import BookSubmission


@pytest.mark.django_db
def test_my_books_add_remove_is_idempotent_and_serialized(client):
    user = User.objects.create_user(email="my-books@example.com", password="strong-password-123")
    book = Book.objects.create(title="My Books Candidate", state="ready", review_state="approved")
    client.force_login(user)

    list_response = client.get("/api/catalog/books/")
    assert list_response.status_code == 200
    row = next(entry for entry in list_response.json() if entry["id"] == str(book.id))
    assert row["is_in_my_books"] is False
    assert row["my_books_added_at"] is None

    first_add = client.post(f"/api/catalog/books/{book.slug}/my-books/")
    second_add = client.post(f"/api/catalog/books/{book.slug}/my-books/")
    assert first_add.status_code == 200
    assert second_add.status_code == 200
    assert UserBook.objects.filter(user=user, book=book).count() == 1
    assert first_add.json()["is_in_my_books"] is True
    assert first_add.json()["my_books_added_at"]

    mine_response = client.get("/api/catalog/books/?ownership=mine")
    assert mine_response.status_code == 200
    assert [entry["id"] for entry in mine_response.json()] == [str(book.id)]
    assert mine_response.json()[0]["is_in_my_books"] is True

    detail_response = client.get(f"/api/catalog/books/{book.slug}/")
    assert detail_response.status_code == 200
    assert detail_response.json()["is_in_my_books"] is True

    first_remove = client.delete(f"/api/catalog/books/{book.slug}/my-books/")
    second_remove = client.delete(f"/api/catalog/books/{book.slug}/my-books/")
    assert first_remove.status_code == 204
    assert second_remove.status_code == 204
    assert not UserBook.objects.filter(user=user, book=book).exists()
    assert client.get("/api/catalog/books/?ownership=mine").json() == []


@pytest.mark.django_db
def test_linked_submission_creates_my_books_ownership(client):
    user = User.objects.create_user(email="submission-owner@example.com", password="strong-password-123")
    book = Book.objects.create(title="Submission Owned Book", state="ready", review_state="approved")

    BookSubmission.objects.create(
        submitter=user,
        input_type="url",
        original_input="https://www.example.com/books/submission-owned-book/",
        normalized_input="https://www.example.com/books/submission-owned-book/",
        resolved_url="https://www.example.com/books/submission-owned-book/",
        resolution_status="resolved",
        status="ready",
        linked_book=book,
    )

    assert UserBook.objects.filter(user=user, book=book).exists()
    client.force_login(user)
    mine_response = client.get("/api/catalog/books/?ownership=mine")
    assert [entry["id"] for entry in mine_response.json()] == [str(book.id)]
