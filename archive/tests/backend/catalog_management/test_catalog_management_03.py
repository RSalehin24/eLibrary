import json
from datetime import timedelta
from pathlib import Path

import pytest
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from django.utils.text import slugify

from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookContributor,
    BookSource,
    CATALOG_CODE_LENGTH,
    Category,
    Contributor,
    derive_category_catalog_code_from_book_code,
    derive_writer_catalog_code_from_book_code,
    GeneratedAsset,
    GeneratedAssetType,
    MetadataReview,
    MetadataVersion,
    Series,
)
from apps.catalog.services import get_or_create_category, get_or_create_contributor, get_or_create_series, replace_book_relations
from apps.ingestion.models import BookSubmission, DuplicateReview, ProcessingJob


@pytest.mark.django_db
def test_staff_can_confirm_duplicate_review_to_existing_book(client):
    admin = User.objects.create_superuser(email="review-admin@example.com", password="strong-password-123")
    submitter = User.objects.create_user(email="submitter2@example.com", password="strong-password-123")
    existing_book = Book.objects.create(title="বিদ্যমান বই", state="ready", review_state="approved")
    submission = BookSubmission.objects.create(
        submitter=submitter,
        input_type="title",
        original_input="বিদ্যমান বই",
        normalized_input="বিদ্যমান বই",
        resolved_url="https://www.example.com/books/existing-title/",
        resolution_status="resolved",
        resolution_confidence=0.82,
        status="duplicate",
        review_state="needs_review",
    )
    review = DuplicateReview.objects.create(submission=submission, existing_book=existing_book)
    client.force_login(admin)

    response = client.post(
        f"/api/ingestion/duplicate-reviews/{review.id}/resolve/",
        data=json.dumps({"decision": "confirm_existing", "notes": "Confirmed by staff"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    submission.refresh_from_db()
    review.refresh_from_db()

    assert submission.linked_book_id == existing_book.id
    assert submission.status == "ready"
    assert review.status == "confirmed"


@pytest.mark.django_db
def test_metadata_edit_scope_allows_non_staff_editor(client):
    editor = User.objects.create_user(email="editor@example.com", password="strong-password-123")
    book = Book.objects.create(title="সম্পাদনাযোগ্য বই", state="ready", review_state="needs_review")
    PermissionGrant.objects.create(user=editor, book=book, scope=PermissionScope.METADATA_EDIT)
    client.force_login(editor)

    response = client.patch(
        f"/api/catalog/books/{book.slug}/metadata/",
        data=json.dumps({"summary": "সম্পাদিত সারাংশ", "notes": "Scoped editor"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    book.refresh_from_db()
    assert book.summary == "সম্পাদিত সারাংশ"


@pytest.mark.django_db
def test_metadata_update_drops_author_role_when_same_name_is_translator_or_editor(client):
    admin = User.objects.create_superuser(email="dedupe-admin@example.com", password="strong-password-123")
    book = Book.objects.create(title="রোল সাজানো বই", state="ready", review_state="pending")
    client.force_login(admin)

    response = client.patch(
        f"/api/catalog/books/{book.slug}/metadata/",
        data=json.dumps(
            {
                "contributors": [
                    {"name": "ইশরাক অর্ণব", "role": "author"},
                    {"name": "ইশরাক অর্ণব", "role": "translator"},
                    {"name": "কেইগো হিগাশিনো", "role": "author"},
                    {"name": "কেইগো হিগাশিনো", "role": "editor"},
                ],
                "notes": "Normalize contributor roles",
            }
        ),
        content_type="application/json",
    )

    assert response.status_code == 200
    contributor_roles = {(relation.contributor.name, relation.role) for relation in book.book_contributors.all()}
    assert ("ইশরাক অর্ণব", "translator") in contributor_roles
    assert ("কেইগো হিগাশিনো", "editor") in contributor_roles
    assert ("ইশরাক অর্ণব", "author") not in contributor_roles
    assert ("কেইগো হিগাশিনো", "author") not in contributor_roles


@pytest.mark.django_db
def test_metadata_edit_scope_allows_non_staff_editor_to_soft_delete_book(client):
    editor = User.objects.create_user(email="delete-editor@example.com", password="strong-password-123")
    book = Book.objects.create(title="মুছে ফেলার বই", state="ready", review_state="approved")
    PermissionGrant.objects.create(user=editor, book=book, scope=PermissionScope.METADATA_EDIT)
    client.force_login(editor)

    response = client.delete(f"/api/catalog/books/{book.slug}/")

    assert response.status_code == 204
    book.refresh_from_db()
    assert book.deleted_at is not None
    assert book.state == "soft_deleted"


@pytest.mark.django_db
def test_book_delete_requires_metadata_edit_scope(client):
    user = User.objects.create_user(email="reader-delete@example.com", password="strong-password-123")
    book = Book.objects.create(title="নিরাপদ বই", state="ready", review_state="approved")
    client.force_login(user)

    response = client.delete(f"/api/catalog/books/{book.slug}/")

    assert response.status_code == 403
    book.refresh_from_db()
    assert book.deleted_at is None


@pytest.mark.django_db
def test_processing_manage_scope_allows_non_staff_duplicate_resolution(client):
    reviewer = User.objects.create_user(email="processor@example.com", password="strong-password-123")
    submitter = User.objects.create_user(email="submitter3@example.com", password="strong-password-123")
    existing_book = Book.objects.create(title="প্রসেসিং বই", state="ready", review_state="approved")
    submission = BookSubmission.objects.create(
        submitter=submitter,
        input_type="title",
        original_input="প্রসেসিং বই",
        normalized_input="প্রসেসিং বই",
        resolved_url="https://www.example.com/books/processing-book/",
        resolution_status="resolved",
        resolution_confidence=0.8,
        status="duplicate",
        review_state="needs_review",
    )
    review = DuplicateReview.objects.create(submission=submission, existing_book=existing_book)
    PermissionGrant.objects.create(user=reviewer, scope=PermissionScope.PROCESSING_MANAGE)
    client.force_login(reviewer)

    response = client.post(
        f"/api/ingestion/duplicate-reviews/{review.id}/resolve/",
        data=json.dumps({"decision": "confirm_existing", "notes": "Scoped reviewer"}),
        content_type="application/json",
    )

    assert response.status_code == 200
    submission.refresh_from_db()
    assert submission.linked_book_id == existing_book.id


@pytest.mark.django_db
def test_metadata_review_endpoints_update_book_review_state(client):
    editor = User.objects.create_user(email="reviewer@example.com", password="strong-password-123")
    book = Book.objects.create(title="রিভিউ বই", state="ready", review_state="needs_review")
    PermissionGrant.objects.create(user=editor, book=book, scope=PermissionScope.METADATA_EDIT)
    client.force_login(editor)

    created = client.post(
        f"/api/catalog/books/{book.slug}/metadata-reviews/",
        data=json.dumps({"state": "approved", "notes": "Reviewed and approved"}),
        content_type="application/json",
    )
    assert created.status_code == 201
    book.refresh_from_db()
    assert book.review_state == "approved"
    assert MetadataReview.objects.filter(book=book).count() == 1

    listed = client.get(f"/api/catalog/books/{book.slug}/metadata-reviews/")
    assert listed.status_code == 200
    assert listed.json()[0]["state"] == "approved"

    updated = client.patch(
        f"/api/catalog/metadata-reviews/{created.json()['id']}/",
        data=json.dumps({"state": "rejected", "notes": "Needs more work"}),
        content_type="application/json",
    )
    assert updated.status_code == 200
    book.refresh_from_db()
    assert book.review_state == "rejected"
