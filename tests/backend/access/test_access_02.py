from pathlib import Path
from urllib.parse import quote

import pytest
from bs4 import BeautifulSoup
from django.core.files.base import ContentFile

from apps.access.models import PermissionGrant, PermissionScope, PreviewAccessSession
from apps.accounts.models import User
from apps.catalog.models import (
    Book,
    BookCategory,
    BookContributor,
    Category,
    Contributor,
    ContributorRole,
    GeneratedAsset,
    GeneratedAssetStatus,
    GeneratedAssetType,
)
from apps.common.permissions import user_has_scope
from apps.ingestion.models import BookSubmission, ResolutionStatus, SubmissionStatus
from apps.access.views import normalize_preview_book_sections


def assert_content_disposition_filename(header_value, expected_filename):
    assert (
        f'filename="{expected_filename}"' in header_value
        or f"filename*=utf-8''{quote(expected_filename)}" in header_value
    )


def test_normalize_preview_book_sections_cleans_redundant_dedication_heading():
        soup = BeautifulSoup(
                """
                <html>
                    <body>
                        <div class='dedication-section'>
                            <h2 class='dedication-title'>উৎসর্গ</h2>
                            <div class='dedication-content'>
                                <p>উৎসর্গ</p>
                                <p><strong>উৎসর্গ :</strong></p>
                                <p>পাঠক, আপনাকে…</p>
                            </div>
                        </div>
                        <div class='main-content'>
                            <p>এটাই মূল কনটেন্ট।</p>
                        </div>
                    </body>
                </html>
                """,
                "html.parser",
        )

        updated = normalize_preview_book_sections(soup)

        assert updated is True
        dedication_content = soup.find("div", class_="dedication-content")
        assert dedication_content is not None
        dedication_text = dedication_content.get_text(" ", strip=True)
        assert dedication_text.startswith("পাঠক, আপনাকে")


def test_normalize_preview_book_sections_inserts_dedication_from_book_data_when_missing():
        soup = BeautifulSoup(
                """
                <html>
                    <body>
                        <div class='main-content'>
                            <p>এটাই মূল কনটেন্ট।</p>
                        </div>
                    </body>
                </html>
                """,
                "html.parser",
        )

        updated = normalize_preview_book_sections(
                soup,
            dedication_html="<p>উৎসর্গ : পাঠক, আপনাকে…</p>",
        )

        assert updated is True
        dedication_content = soup.find("div", class_="dedication-content")
        assert dedication_content is not None
        dedication_text = dedication_content.get_text(" ", strip=True)
        assert dedication_text.startswith("পাঠক, আপনাকে")


def test_normalize_preview_book_sections_inserts_dedication_without_main_content():
        soup = BeautifulSoup(
                """
                <html>
                    <body>
                        <div class='container'>
                            <div class='book-header'></div>
                            <div class='toc-section'></div>
                        </div>
                    </body>
                </html>
                """,
                "html.parser",
        )

        updated = normalize_preview_book_sections(
                soup,
            dedication_html="<p>উৎসর্গ : পাঠক, আপনাকে…</p>",
        )

        assert updated is True
        dedication_section = soup.find("div", class_="dedication-section")
        assert dedication_section is not None
        dedication_content = dedication_section.find("div", class_="dedication-content")
        assert dedication_content is not None
        dedication_text = dedication_content.get_text(" ", strip=True)
        assert dedication_text.startswith("পাঠক, আপনাকে")


def test_normalize_preview_book_sections_keeps_standard_dedication_title():
        soup = BeautifulSoup(
                """
                <html>
                    <body>
                        <div class='dedication-section'>
                            <h2 class='dedication-title'>উৎসর্গ</h2>
                            <div class='dedication-content'>
                                <p>স্ট্যানলির স্মৃতির প্রতি</p>
                                <p>তোমাকে শ্রদ্ধা।</p>
                            </div>
                        </div>
                        <div class='main-content'>
                            <p>এটাই মূল কনটেন্ট।</p>
                        </div>
                    </body>
                </html>
                """,
                "html.parser",
        )

        updated = normalize_preview_book_sections(soup)

        assert updated is True
        dedication_title = soup.find("h2", class_="dedication-title")
        dedication_content = soup.find("div", class_="dedication-content")
        assert dedication_title is not None
        assert dedication_title.get_text(strip=True) == "উৎসর্গ"
        assert dedication_content is not None
        assert "তোমাকে শ্রদ্ধা।" in dedication_content.get_text(" ", strip=True)


def test_normalize_preview_book_sections_uses_english_dedication_heading_when_content_is_english():
        soup = BeautifulSoup(
                """
                <html>
                    <body>
                        <div class='dedication-section'>
                            <h2 class='dedication-title'>উৎসর্গ</h2>
                            <div class='dedication-content'>
                                <p>Dedication</p>
                                <p>For everyone who kept reading.</p>
                            </div>
                        </div>
                        <div class='main-content'>
                            <p>Main content.</p>
                        </div>
                    </body>
                </html>
                """,
                "html.parser",
        )

        updated = normalize_preview_book_sections(soup)

        assert updated is True
        dedication_title = soup.find("h2", class_="dedication-title")
        dedication_content = soup.find("div", class_="dedication-content")
        assert dedication_title is not None
        assert dedication_title.get_text(strip=True) == "Dedication"
        assert dedication_content is not None
        assert "Dedication" not in dedication_content.get_text(" ", strip=True)
        assert "For everyone who kept reading." in dedication_content.get_text(" ", strip=True)


def test_normalize_preview_book_sections_extracts_leading_front_sections_from_main_content():
        soup = BeautifulSoup(
                """
                <html>
                    <body>
                        <div class='container'>
                            <div class='main-content'>
                                <h2>সহস্রাব্দ সংস্করণের কথা</h2>
                                <p>এই অংশটি সামনের নোট।</p>
                                <h2>প্রারম্ভ কথন</h2>
                                <p>এটিও মূল বইয়ের আগে থাকা অংশ।</p>
                                <h2>অধ্যায় ১</h2>
                                <p>এটাই মূল কনটেন্ট।</p>
                            </div>
                        </div>
                    </body>
                </html>
                """,
                "html.parser",
        )

        updated = normalize_preview_book_sections(soup)

        assert updated is True
        front_titles = [
            node.get_text(strip=True)
            for node in soup.find_all("h2", class_="front-section-title")
        ]
        assert "সহস্রাব্দ সংস্করণের কথা" in front_titles
        assert "প্রারম্ভ কথন" in front_titles

        main_content = soup.find("div", class_="main-content")
        assert main_content is not None
        main_text = main_content.get_text(" ", strip=True)
        assert "এই অংশটি সামনের নোট।" not in main_text
        assert "এটিও মূল বইয়ের আগে থাকা অংশ।" not in main_text
        assert "এটাই মূল কনটেন্ট।" in main_text


@pytest.mark.django_db
def test_missing_stored_asset_returns_404_and_marks_asset_failed(client):
    user = User.objects.create_user(email="missing-asset@example.com", password="strong-password-123")
    book = Book.objects.create(title="Missing Asset Book", state="ready", review_state="approved")
    asset = GeneratedAsset.objects.create(
        book=book,
        asset_type=GeneratedAssetType.COVER,
        status=GeneratedAssetStatus.READY,
        content_type="image/jpeg",
    )
    asset.file.save("book_cover.jpg", ContentFile(b"cover-bytes"), save=True)
    broken_path = Path(asset.file.path)
    broken_path.unlink()

    PermissionGrant.objects.create(user=user, book=book, scope=PermissionScope.PREVIEW_HTML)
    client.force_login(user)

    response = client.get(f"/api/access/books/{book.slug}/download/cover/")

    assert response.status_code == 404
    assert response.json()["detail"] == "This file is no longer available in storage. Please regenerate the book."

    asset.refresh_from_db()
    book.refresh_from_db()
    assert asset.status == GeneratedAssetStatus.FAILED
    assert asset.file.name == ""
    assert book.state == "needs_review"
    assert book.review_state == "needs_review"
