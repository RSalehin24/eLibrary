from dataclasses import replace
from uuid import uuid4

import pytest
from apps.accounts.mail_configuration import kindle_sender_email
from apps.accounts.models import User
from apps.catalog.models import Book, GeneratedAsset
from apps.processing.job_models import BackgroundJobKind
from apps.processing.jobs.commands import JobCommand, enqueue_job
from automation_fixtures import create_automation
from regeneration_fixtures import create_regeneration_fixture
from source_processing_fixtures import create_source_job, curated_source

from tests.backend.access.reader_fixtures import write_epub


@pytest.fixture
def automation(settings):
    return create_automation(settings)


@pytest.fixture
def command():
    actor = User.objects.create_user(email="background-job@library.test")
    book = Book.objects.create(title="পটভূমির কাজের পরীক্ষার বই")
    asset = GeneratedAsset.objects.create(book=book, asset_type="epub", status="ready")
    return JobCommand(uuid4(), actor, asset, BackgroundJobKind.PREPARE_EPUB)


@pytest.fixture
def preparation_job(command, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path / "media"
    command.actor.is_staff = True
    command.actor.save()
    command.asset.legacy_path = str(write_epub(tmp_path / "job.epub"))
    command.asset.save()
    command = replace(
        command, values={"asset_revision": command.asset.updated_at.isoformat()}
    )
    return enqueue_job(command)


@pytest.fixture
def kindle_job(command, preparation_job, settings):
    settings.ACCOUNT_INVITE_FROM_EMAIL = "library@example.test"
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    actor = preparation_job.requested_by
    actor.kindle_emails = ["reader@kindle.com", "other@kindle.com"]
    actor.save()
    values = {
        "asset_revision": preparation_job.asset.updated_at.isoformat(),
        "recipients": actor.kindle_emails,
        "sender": kindle_sender_email(),
        "subject": preparation_job.book.title,
    }
    return enqueue_job(
        replace(
            command,
            identifier=uuid4(),
            actor=actor,
            asset=preparation_job.asset,
            kind=BackgroundJobKind.DELIVER_KINDLE,
            values=values,
        )
    )


@pytest.fixture
def source_job(settings, tmp_path):
    settings.SOURCE_SITE_HOST = "source.test"
    settings.SOURCE_SITE_FALLBACK_HOSTS = []
    settings.RUNTIME_STORAGE_DIR = tmp_path
    settings.MEDIA_ROOT = tmp_path / "media"
    return create_source_job()


@pytest.fixture
def curated_job(source_job, tmp_path):
    from apps.ingestion.source_processing.storage import write_artifact

    result = curated_source(tmp_path)
    assert result["status"] == "validated"
    source_job.checkpoint = {"document_ref": write_artifact(source_job.pk, result)}
    source_job.save()
    return source_job


@pytest.fixture
def regeneration(source_job, tmp_path):
    return create_regeneration_fixture(source_job, tmp_path)
