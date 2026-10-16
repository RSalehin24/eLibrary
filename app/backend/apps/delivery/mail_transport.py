import logging
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Protocol

from django.core.mail import BadHeaderError, EmailMessage
from django.core.mail.backends.smtp import EmailBackend

from apps.accounts.mail_configuration import (
    SMTP_EMAIL_BACKEND,
    build_kindle_delivery_connection_kwargs,
)
from apps.delivery.mail_errors import (
    MAIL_TRANSPORT_ERRORS,
    connection_failure,
    submission_failure,
)
from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class KindleMessage:
    subject: str
    sender: str
    recipient: str
    filename: str
    content: bytes


@dataclass(frozen=True)
class TextMessage:
    subject: str
    sender: str
    recipient: str
    body: str


class Mailer(Protocol):
    def open(self) -> None: ...
    def send(self, message: KindleMessage | TextMessage) -> None: ...
    def close(self) -> None: ...


def checked_mail_parameters():
    parameters = build_kindle_delivery_connection_kwargs()
    backend = parameters.pop("backend")
    if backend != SMTP_EMAIL_BACKEND or not parameters.get("host"):
        raise ExecutionFailure(FailureKind.PERMANENT, "mail_configuration_missing")
    if not 1 <= parameters["port"] <= 65535 or not 1 <= parameters["timeout"] <= 60:
        raise ExecutionFailure(FailureKind.PERMANENT, "mail_configuration_invalid")
    if parameters["use_tls"] and parameters["use_ssl"]:
        raise ExecutionFailure(FailureKind.PERMANENT, "mail_configuration_invalid")
    return parameters


def email_message(message: KindleMessage | TextMessage):
    email = EmailMessage(
        subject=message.subject,
        body=message.body if isinstance(message, TextMessage) else "",
        from_email=message.sender,
        to=[message.recipient],
    )
    if isinstance(message, KindleMessage):
        email.attach(message.filename, message.content, "application/epub+zip")
    return email


def validate_message(message: KindleMessage | TextMessage):
    try:
        email_message(message).message()
    except (BadHeaderError, ValueError, UnicodeError):
        raise ExecutionFailure(FailureKind.PERMANENT, "message_invalid") from None


class SMTPMailer:
    def __init__(self):
        self.connection = EmailBackend(**checked_mail_parameters())

    def open(self):
        try:
            self.connection.open()
        except MAIL_TRANSPORT_ERRORS as error:
            raise connection_failure(error) from None

    def send(self, message: KindleMessage | TextMessage):
        email = email_message(message)
        email.connection = self.connection
        try:
            accepted = email.send(fail_silently=False)
        except MAIL_TRANSPORT_ERRORS as error:
            raise submission_failure(error) from None
        if accepted != 1:
            raise ExecutionFailure(FailureKind.TRANSIENT, "message_not_accepted")

    def close(self):
        self.connection.close()


SMTPKindleMailer = SMTPMailer


@contextmanager
def connected_mailer(mailer: Mailer, job_id, mail_kind="Kindle"):
    try:
        mailer.open()
        yield mailer
    finally:
        try:
            mailer.close()
        except MAIL_TRANSPORT_ERRORS:
            # SMTP QUIT failure cannot reverse an already confirmed acceptance.
            logger.warning(
                "%s SMTP cleanup failed.", mail_kind, extra={"job_id": str(job_id)}
            )
