from contextlib import nullcontext
from email.parser import BytesParser
from email.policy import default

import pytest
from apps.processing.jobs.worker import run_background_job
from smtp_fixture import local_smtp

pytestmark = pytest.mark.django_db


def use_local_smtp(settings, server):
    settings.EMAIL_HOST = "127.0.0.1"
    settings.EMAIL_PORT = server.server_address[1]
    settings.EMAIL_USE_TLS = settings.EMAIL_USE_SSL = False
    settings.EMAIL_HOST_USER = settings.EMAIL_HOST_PASSWORD = ""
    settings.EMAIL_TIMEOUT = 5


def run_dispatch(job):
    run_background_job(job.dispatches.get().pk, lambda _: nullcontext())
    job.refresh_from_db()


def test_real_smtp_acceptance_stores_each_recipient_and_attaches_the_epub(
    kindle_job, settings
):
    with local_smtp("accept") as server:
        use_local_smtp(settings, server)
        run_dispatch(kindle_job)
        assert kindle_job.state == "succeeded" and len(server.messages) == 2
        message = BytesParser(policy=default).parsebytes(server.messages[0])
        attachment = next(message.iter_attachments())
        assert str(message["Subject"]) == kindle_job.input["subject"]
        assert attachment.get_content_type() == "application/epub+zip"
        assert attachment.get_payload(decode=True).startswith(b"PK")


def test_smtp_connection_loss_after_data_requires_review_and_repeated_delivery_cannot_resend(
    kindle_job, settings
):
    with local_smtp("disconnect") as server:
        use_local_smtp(settings, server)
        run_dispatch(kindle_job)
        assert len(server.messages) == 1 and kindle_job.state == "needs_attention"
        assert (
            kindle_job.error_code == "mail_acceptance_unknown"
            and kindle_job.dispatches.count() == 1
        )
        run_dispatch(kindle_job)
        assert len(server.messages) == 1
