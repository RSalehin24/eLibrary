import json
import os
import secrets
from pathlib import Path
from uuid import uuid4

import django
from seed_reader import create_reading_book


def create_session(user):
    from django.conf import settings
    from django.contrib.auth import BACKEND_SESSION_KEY, HASH_SESSION_KEY, SESSION_KEY
    from django.contrib.sessions.backends.db import SessionStore

    session = SessionStore()
    session[SESSION_KEY] = str(user.pk)
    session[BACKEND_SESSION_KEY] = settings.AUTHENTICATION_BACKENDS[0]
    session[HASH_SESSION_KEY] = user.get_session_auth_hash()
    session.save()
    return {"name": settings.SESSION_COOKIE_NAME, "value": session.session_key}


def create_account(identity, role):
    from apps.accounts.models import User

    password = secrets.token_urlsafe(24)
    user = User.objects.create_user(
        email=f"foundation-{role}-{identity}@example.test",
        password=password,
        full_name=f"Foundation {role}",
        is_staff=role == "administrator",
        totp_required=False,
    )
    return user, {
        "id": user.pk,
        "email": user.email,
        "password": password,
        "session": create_session(user),
    }


def create_books(identity):
    from apps.catalog.models import (
        Book,
        BookCategory,
        BookContributor,
        Category,
        Contributor,
    )
    from apps.catalog.services import sync_book_catalog_code
    from apps.common.models import LifecycleState, ReviewState
    from django.utils import timezone

    author = Contributor.objects.create(name=f"পরীক্ষার লেখক {identity}")
    category = Category.objects.create(name=f"পরীক্ষার গল্প {identity}")
    books = []
    for number in range(25):
        book = Book.objects.create(
            title=f"পরীক্ষার বই {identity} {number + 1}",
            summary="এটি স্থানীয় পরীক্ষার জন্য তৈরি বইয়ের পরিচিতি।",
            editorial_description="এটি স্থানীয় পরীক্ষার জন্য পর্যালোচিত সম্পাদকীয় পরিচিতি।",
            editorial_reviewed_at=timezone.now(),
            indexing_eligible=True,
            state=LifecycleState.PUBLISHED,
            review_state=ReviewState.APPROVED,
        )
        BookContributor.objects.create(book=book, contributor=author, role="author")
        BookCategory.objects.create(book=book, category=category)
        sync_book_catalog_code(book)
        books.append(book)
    return books


def create_collection(identity, books):
    from apps.catalog.models import CollectionBook, CuratedCollection
    from django.utils import timezone

    collection = CuratedCollection.objects.create(
        name=f"পরীক্ষার নির্বাচন {identity}",
        state="published",
        editorial_description="এটি স্থানীয় পরীক্ষার জন্য পর্যালোচিত তিন বইয়ের নির্বাচিত সংগ্রহ।",
        editorial_reviewed_at=timezone.now(),
        indexing_eligible=True,
    )
    for position, book in enumerate(books[:3]):
        CollectionBook.objects.create(
            collection=collection, book=book, position=position
        )
    return {"slug": collection.slug, "name": collection.name}


def require_foundation_database():
    from django.conf import settings

    database = settings.DATABASES["default"]
    if (
        settings.APP_ENV == "production"
        or database["NAME"] != "bangla_library"
        or str(database["PORT"]) != "55432"
    ):
        raise RuntimeError("Browser fixtures require bangla_library on port 55432.")


def seed_fixture():
    from apps.access.models import PermissionGrant, PermissionScope, ReadingSession
    from apps.catalog.models import Book, UserBook
    from django.db import transaction

    require_foundation_database()
    identity = uuid4().hex[:8]
    with transaction.atomic():
        books = create_books(identity)
        collection = create_collection(identity, books)
        owner, reader = create_account(identity, "reader")
        administrator_user, administrator = create_account(identity, "administrator")
        from seed_lifecycle import (
            create_lifecycle_fixture,
            create_reader_update_fixture,
        )

        lifecycle_books = create_lifecycle_fixture(administrator_user)
        reader_update_books = create_reader_update_fixture(administrator_user)
        _, maintenance_administrator = create_account(uuid4().hex[:8], "administrator")
        _, catalog_administrator = create_account(uuid4().hex[:8], "administrator")
        editor, scoped_editor = create_account(identity, "editor")
        from seed_entities import create_entity_fixture

        entities = create_entity_fixture(identity, editor)
        from seed_personal import create_personal_fixture

        personal = create_personal_fixture(identity, books, create_account)
        UserBook.objects.create(user=owner, book=books[0])
        ReadingSession.objects.create(
            user=owner, book=books[0], progress_percent=42, last_location="chapter-2"
        )
        PermissionGrant.objects.create(
            user=editor, book=books[0], scope=PermissionScope.METADATA_EDIT
        )
        draft = Book.objects.create(title=f"সম্পাদনার পরীক্ষা {uuid4().hex[:8]}")
        PermissionGrant.objects.create(
            user=editor, book=draft, scope=PermissionScope.METADATA_EDIT
        )
        conflict = Book.objects.create(title=f"সমান্তরাল সম্পাদনা {uuid4().hex[:8]}")
        PermissionGrant.objects.create(
            user=editor, book=conflict, scope=PermissionScope.METADATA_EDIT
        )
        reading_user, reading_reader = create_account(uuid4().hex[:8], "reading-reader")
        reading_book = create_reading_book(reading_user)
        from seed_legacy_reader import create_legacy_reader_fixture

        legacy_user, legacy_reader = create_account(uuid4().hex[:8], "legacy-reader")
        legacy_reading = create_legacy_reader_fixture(legacy_user)
        kindle_user, kindle_reader = create_account(uuid4().hex[:8], "kindle-reader")
        kindle_user.kindle_emails = ["reader@kindle.com", "other@kindle.com"]
        kindle_user.save(update_fields=["kindle_emails"])
        UserBook.objects.create(user=kindle_user, book_id=reading_book["id"])
        preparation_job = create_preparation_job(
            administrator_user, reading_book["slug"]
        )
        update_user, update_reader = create_account(uuid4().hex[:8], "update-reader")
        update_book = create_reading_book(update_user)
        profile_user, profile_reader = create_account(identity, "profile-reader")
        UserBook.objects.create(user=profile_user, book=books[0])
        security_user, security_reader = create_account(identity, "security-reader")
        security_reader["previous_session"] = create_session(security_user)
        required_user, required_reader = create_account(identity, "required-reader")
        required_user.totp_required = True
        required_user.save(update_fields=["totp_required", "updated_at"])
        required_reader["session"] = create_session(required_user)
        access_user, access_manager = create_account(identity, "access-manager")
        PermissionGrant.objects.create(
            user=access_user, scope=PermissionScope.ACCESS_MANAGE
        )
        _, managed_reader = create_account(identity, "managed-reader")
        _, access_conflict_reader = create_account(identity, "access-conflict-reader")
        reset_user, reset_reader = create_account(identity, "password-reset-reader")
        reset_reader.update(password_link_values(reset_user))
        setup_reader = create_password_setup_account(identity)
        from seed_sources import create_source_fixture, grant_source_processing

        source_user, source_processor = create_account(identity, "source-processor")
        grant_source_processing(source_user)
        sources = create_source_fixture(identity, reading_book)
        from seed_overview import create_overview_fixture

        overview = create_overview_fixture(
            administrator_user, access_user, preparation_job
        )
        from seed_source_processing import create_source_processing_fixture

        source_processing = create_source_processing_fixture(source_user)
    return {
        "reader": reader,
        "administrator": administrator,
        "maintenance_administrator": maintenance_administrator,
        "catalog_administrator": catalog_administrator,
        "editor": scoped_editor,
        "entities": entities,
        "personal": personal,
        "personal_reader": personal["account"],
        "book": {"slug": books[0].slug, "title": books[0].title},
        "editorial_book": {"slug": draft.slug, "title": draft.title},
        "conflict_book": {"slug": conflict.slug, "title": conflict.title},
        "collection": collection,
        "query": identity,
        "reading_reader": reading_reader,
        "kindle_reader": kindle_reader,
        "reading_book": reading_book,
        "legacy_reader": legacy_reader,
        "legacy_reading": legacy_reading,
        "preparation_job": preparation_job,
        "update_reader": update_reader,
        "update_book": update_book,
        "profile_reader": profile_reader,
        "security_reader": security_reader,
        "required_reader": required_reader,
        "access_manager": access_manager,
        "managed_reader": managed_reader,
        "access_conflict_reader": access_conflict_reader,
        "password_reset_reader": reset_reader,
        "password_setup_reader": setup_reader,
        "source_processor": source_processor,
        "sources": sources,
        "overview": overview,
        "source_processing": source_processing,
        "lifecycle_books": lifecycle_books,
        "reader_update_books": reader_update_books,
    }


def create_preparation_job(actor, slug):
    from apps.catalog.models import GeneratedAsset
    from apps.processing.jobs.requests import PreparationRequest, request_preparation

    asset = GeneratedAsset.objects.get(book__slug=slug, asset_type="epub")
    job = request_preparation(
        actor, PreparationRequest(uuid4(), asset.pk, asset.updated_at)
    )
    return {"id": str(job.pk)}


def password_link_values(user):
    from apps.accounts.serializers.support import password_link_token_generator
    from django.utils.encoding import force_bytes
    from django.utils.http import urlsafe_base64_encode

    return {
        "id": user.pk,
        "email": user.email,
        "new_password": f"  {secrets.token_urlsafe(24)}  ",
        "uid": urlsafe_base64_encode(force_bytes(user.pk)),
        "token": password_link_token_generator.make_token(user),
    }


def create_password_setup_account(identity):
    from apps.accounts.models import User

    user = User.objects.create_user(
        email=f"foundation-password-setup-{identity}@example.test",
        full_name="প্রথম প্রবেশের পাঠক",
        email_setup_pending=True,
        totp_required=True,
    )
    return password_link_values(user)


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()
    output = Path(os.environ["FOUNDATION_FIXTURE_PATH"])
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        json.dump(seed_fixture(), stream)


if __name__ == "__main__":
    main()
