from smtplib import (
    SMTPAuthenticationError,
    SMTPDataError,
    SMTPRecipientsRefused,
    SMTPServerDisconnected,
)
from unittest.mock import Mock

import pytest
from apps.delivery.mail_errors import connection_failure, submission_failure
from apps.delivery.mail_transport import (
    KindleMessage,
    SMTPKindleMailer,
    checked_mail_parameters,
    connected_mailer,
    validate_message,
)
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


@pytest.mark.parametrize(
    "error,kind,code",
    [
        (
            SMTPAuthenticationError(535, b"synthetic"),
            FailureKind.PERMANENT,
            "mail_authentication_failed",
        ),
        (
            SMTPRecipientsRefused({"reader@kindle.com": (450, b"synthetic")}),
            FailureKind.TRANSIENT,
            "recipient_rejected",
        ),
        (
            SMTPRecipientsRefused({"reader@kindle.com": (550, b"synthetic")}),
            FailureKind.PERMANENT,
            "recipient_rejected",
        ),
        (SMTPDataError(451, b"synthetic"), FailureKind.TRANSIENT, "message_rejected"),
        (SMTPDataError(554, b"synthetic"), FailureKind.PERMANENT, "message_rejected"),
        (
            SMTPServerDisconnected("synthetic"),
            FailureKind.UNCERTAIN,
            "mail_acceptance_unknown",
        ),
        (TimeoutError("synthetic"), FailureKind.UNCERTAIN, "mail_acceptance_unknown"),
    ],
)
def test_mail_submission_distinguishes_known_rejection_from_uncertain_acceptance(
    error, kind, code
):
    failure = submission_failure(error).failure
    assert failure.kind == kind and failure.code == code


def test_connection_failure_before_submission_is_safe_to_retry():
    assert (
        connection_failure(SMTPServerDisconnected("synthetic")).failure.kind
        == FailureKind.TRANSIENT
    )


def test_mail_configuration_requires_real_smtp_and_supports_a_private_relay_without_credentials(
    settings,
):
    settings.EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
    with pytest.raises(ExecutionFailure, match="mail_configuration_missing"):
        checked_mail_parameters()
    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    settings.EMAIL_HOST_USER = settings.EMAIL_HOST_PASSWORD = ""
    parameters = checked_mail_parameters()
    assert (
        parameters["host"] == "127.0.0.1"
        and parameters["username"] == parameters["password"] == ""
    )
    settings.EMAIL_USE_TLS = settings.EMAIL_USE_SSL = True
    with pytest.raises(ExecutionFailure, match="mail_configuration_invalid"):
        checked_mail_parameters()


def test_message_header_validation_happens_before_network_submission():
    invalid = KindleMessage(
        "Book\nBcc: injected@example.test",
        "sender@example.test",
        "reader@kindle.com",
        "book.epub",
        b"synthetic",
    )
    with pytest.raises(ExecutionFailure, match="message_invalid"):
        validate_message(invalid)


def test_smtp_adapter_records_an_acceptance_only_for_one_message(settings, monkeypatch):
    from apps.delivery import mail_transport

    settings.EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    settings.EMAIL_HOST = "127.0.0.1"
    connection = Mock()
    connection.send_messages.return_value = 1
    monkeypatch.setattr(mail_transport, "EmailBackend", lambda **_: connection)
    mailer = SMTPKindleMailer()
    message = KindleMessage(
        "বাংলা বই", "sender@example.test", "reader@kindle.com", "book.epub", b"synthetic"
    )
    mailer.open()
    mailer.send(message)
    sent = connection.send_messages.call_args.args[0][0]
    assert sent.to == ["reader@kindle.com"] and sent.subject == "বাংলা বই"
    assert sent.attachments[0].mimetype == "application/epub+zip"
    connection.send_messages.return_value = 0
    with pytest.raises(ExecutionFailure, match="message_not_accepted"):
        mailer.send(message)


def test_quit_failure_keeps_the_confirmed_business_result(caplog):
    mailer = Mock()
    mailer.close.side_effect = SMTPServerDisconnected("synthetic")
    with connected_mailer(mailer, "synthetic-job"):
        mailer.send(Mock())
    assert mailer.close.call_count == mailer.send.call_count == 1
    assert "Kindle SMTP cleanup failed." in caplog.text
