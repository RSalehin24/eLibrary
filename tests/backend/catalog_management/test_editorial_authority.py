import pytest
from apps.accounts.models import User
from apps.catalog.editorial.service import update_book_editorial, withdraw_book
from apps.catalog.models import Book, MetadataVersion
from django.http import Http404

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("field", ["is_active", "is_staff"])
@pytest.mark.parametrize("action", ["update", "withdraw"])
def test_editorial_mutations_recheck_revoked_administrator_authority(field, action):
    user = User.objects.create_user(
        email="editorial-authority@library.test", is_staff=True
    )
    stale = User.objects.get(pk=user.pk)
    book = Book.objects.create(title="সম্পাদকের বর্তমান অনুমতি", state="published")
    setattr(user, field, False)
    user.save(update_fields=[field, "updated_at"])
    operations = {
        "update": lambda: update_book_editorial(
            stale,
            book.pk,
            {
                "expected_updated_at": book.updated_at,
                "summary": "আর অনুমতি নেই",
            },
        ),
        "withdraw": lambda: withdraw_book(stale, book.pk, book.updated_at),
    }
    with pytest.raises(Http404):
        operations[action]()
    book.refresh_from_db()
    assert book.summary == "" and book.state == "published"
    assert not MetadataVersion.objects.exists()
