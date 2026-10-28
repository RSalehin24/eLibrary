import json

import pytest
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookContributor,
    Category,
    Contributor,
    MetadataVersion,
    Series,
)
from apps.catalog.services import (
    get_or_create_category,
    get_or_create_contributor,
    get_or_create_series,
)
from django.utils.text import slugify


@pytest.mark.django_db
def test_admin_metadata_update_reuses_existing_related_names_and_versions(client):
    admin = User.objects.create_superuser(
        email="admin@example.com", password="strong-password-123"
    )
    author = get_or_create_contributor("লেখক এক")
    series = get_or_create_series("রহস্য সিরিজ")
    category = get_or_create_category("উপন্যাস")
    book = Book.objects.create(title="পরিবর্তনশীল বই", state="published")
    client.force_login(admin)
    response = client.patch(
        f"/api/catalog/books/{book.slug}/metadata/",
        data=json.dumps(
            {
                "expected_updated_at": book.updated_at.isoformat(),
                "summary": "নতুন সারাংশ",
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    book.refresh_from_db()
    response = client.patch(
        f"/api/v1/manage/books/{book.slug}/relationships/",
        data=json.dumps(
            {
                "expected_updated_at": book.updated_at.isoformat(),
                "contributors": [{"id": str(author.pk), "role": "author"}],
                "series_ids": [str(series.pk)],
                "category_ids": [str(category.pk)],
            }
        ),
        content_type="application/json",
    )
    assert response.status_code == 200
    book.refresh_from_db()
    assert book.summary == "নতুন সারাংশ" and book.state == "published"
    assert book.contributors.get().pk == author.pk
    assert (
        book.series_entries.get().pk == series.pk
        and book.categories.get().pk == category.pk
    )
    assert (
        Contributor.objects.count()
        == Series.objects.count()
        == Category.objects.count()
        == 1
    )
    assert MetadataVersion.objects.filter(book=book).count() == 2


@pytest.mark.django_db
def test_book_slug_and_normalized_title_preserve_bengali_marks():
    book = Book.objects.create(title="ম্যালিস", state="ready")

    assert book.title == "ম্যালিস"
    assert book.normalized_title == "ম্যালিস"
    assert book.slug == "ম্যালিস"

    book.title = "ম্যালিস সমগ্র"
    book.save()

    assert book.normalized_title == "ম্যালিস সমগ্র"
    assert book.slug == "ম্যালিস-সমগ্র"


@pytest.mark.django_db
def test_book_allows_duplicate_titles_for_same_source_site():
    first_book = Book.objects.create(title="শ্রেষ্ঠ কবিতা", state="ready")
    second_book = Book.objects.create(title="শ্রেষ্ঠ কবিতা", state="ready")

    assert first_book.normalized_title == "শ্রেষ্ঠ কবিতা"
    assert second_book.normalized_title == "শ্রেষ্ঠ কবিতা"
    assert first_book.slug != second_book.slug
    assert (
        Book.objects.filter(
            source_site="",
            normalized_title="শ্রেষ্ঠ কবিতা",
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_book_detail_lookup_accepts_legacy_slug_for_unicode_titles(client):
    user = User.objects.create_user(
        email="reader@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="ম্যালিস", state="ready")
    client.force_login(user)

    response = client.get(
        f"/api/catalog/books/{slugify(book.title, allow_unicode=True)}/"
    )

    assert response.status_code == 200
    assert response.json()["slug"] == "ম্যালিস"


@pytest.mark.django_db
def test_book_detail_surfaces_front_matter_and_missing_role_contributors(client):
    user = User.objects.create_user(
        email="reader2@example.com", password="strong-password-123"
    )
    book = Book.objects.create(
        title="সাজানো বই",
        state="ready",
        book_info_html="\n        <p><strong>অনুবাদ</strong>: অনুবাদক এক</p>\n        <p><strong>প্রথম প্রকাশ</strong>: ২০০৫</p>\n        <p><strong>প্রকাশক</strong>: প্রকাশনী ঘর</p>\n        ",
    )
    client.force_login(user)

    response = client.get(f"/api/catalog/books/{book.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert {"name": "অনুবাদক এক", "role": "translator"} in payload["contributors"]
    assert {"name": "প্রকাশনী ঘর", "role": "publisher"} in payload["contributors"]
    assert payload["front_matter"] == [
        {
            "key": "first_published",
            "label": "প্রথম প্রকাশ",
            "value": "২০০৫",
            "role": "",
        }
    ]


@pytest.mark.django_db
def test_book_detail_falls_back_to_leading_main_content_front_matter(client):
    user = User.objects.create_user(
        email="reader-main-content@example.com", password="strong-password-123"
    )
    book = Book.objects.create(
        title="ম্যালিস",
        state="ready",
        main_content_html='\n        <div>\n          <h2 class="wp-block-heading">ম্যালিস – কিয়েগো হিগাশিনো</h2>\n          <p><strong>ম্যালিস – কিয়েগো হিগাশিনো</strong><br/>অনুবাদ: সালমান হক, ইশরাক অর্ণব</p>\n          <p>প্রথম প্রকাশ: মার্চ ২০২৩</p>\n          <p><strong>ভূমিকা</strong></p>\n          <p>এটাই মূল কনটেন্ট।</p>\n        </div>\n        ',
    )
    client.force_login(user)

    response = client.get(f"/api/catalog/books/{book.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert {"name": "সালমান হক", "role": "translator"} in payload["contributors"]
    assert {"name": "ইশরাক অর্ণব", "role": "translator"} in payload["contributors"]
    assert {
        "key": "first_published",
        "label": "প্রথম প্রকাশ",
        "value": "মার্চ ২০২৩",
        "role": "",
    } in payload["front_matter"]


@pytest.mark.django_db
def test_book_detail_hides_author_role_when_same_person_is_translator(client):
    user = User.objects.create_user(
        email="reader-roles@example.com", password="strong-password-123"
    )
    book = Book.objects.create(
        title="ভূমিকা সহ বই",
        state="ready",
        book_info_html="\n        <p><strong>অনুবাদ</strong>: ইশরাক অর্ণব</p>\n        ",
    )
    shared_contributor = get_or_create_contributor("ইশরাক অর্ণব")
    other_author = get_or_create_contributor("সালমান হক")
    BookContributor.objects.create(
        book=book, contributor=shared_contributor, role="author", sort_order=0
    )
    BookContributor.objects.create(
        book=book, contributor=other_author, role="author", sort_order=1
    )
    client.force_login(user)

    response = client.get(f"/api/catalog/books/{book.slug}/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["authors"] == ["সালমান হক"]
    assert {"name": "ইশরাক অর্ণব", "role": "translator"} in payload["contributors"]
    assert {"name": "ইশরাক অর্ণব", "role": "author"} not in payload["contributors"]


@pytest.mark.django_db
def test_book_list_includes_translators_for_card_display(client):
    user = User.objects.create_user(
        email="reader-list@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="কার্ড বই", state="ready")
    author = get_or_create_contributor("কেইগো হিগাশিনো")
    translator = get_or_create_contributor("সালমান হক")
    BookContributor.objects.create(
        book=book, contributor=author, role="author", sort_order=0
    )
    BookContributor.objects.create(
        book=book, contributor=translator, role="translator", sort_order=1
    )
    client.force_login(user)

    response = client.get("/api/catalog/books/")

    assert response.status_code == 200
    payload = response.json()[0]
    assert payload["authors"] == ["কেইগো হিগাশিনো"]
    assert {"name": "সালমান হক", "role": "translator"} in payload["contributors"]


@pytest.mark.django_db
def test_book_serializers_keep_author_names_with_initial_periods(client):
    user = User.objects.create_user(
        email="reader-initials@example.com", password="strong-password-123"
    )
    book = Book.objects.create(title="২০০১ : আ স্পেস ওডিসি", state="ready")
    author = get_or_create_contributor("আর্থার সি. ক্লার্ক")
    translator = get_or_create_contributor("মাকসুদুজ্জামান খান")
    BookContributor.objects.create(
        book=book, contributor=author, role="author", sort_order=0
    )
    BookContributor.objects.create(
        book=book, contributor=translator, role="translator", sort_order=1
    )
    client.force_login(user)

    list_response = client.get("/api/catalog/books/")
    detail_response = client.get(f"/api/catalog/books/{book.slug}/")

    assert list_response.status_code == 200
    list_payload = next(
        entry for entry in list_response.json() if entry["slug"] == book.slug
    )
    assert list_payload["authors"] == ["আর্থার সি. ক্লার্ক"]
    assert {"name": "আর্থার সি. ক্লার্ক", "role": "author"} in list_payload["contributors"]
    assert {"name": "মাকসুদুজ্জামান খান", "role": "translator"} in list_payload["contributors"]

    assert detail_response.status_code == 200
    detail_payload = detail_response.json()
    assert detail_payload["authors"] == ["আর্থার সি. ক্লার্ক"]
    assert {"name": "আর্থার সি. ক্লার্ক", "role": "author"} in detail_payload["contributors"]
    assert {"name": "মাকসুদুজ্জামান খান", "role": "translator"} in detail_payload[
        "contributors"
    ]
