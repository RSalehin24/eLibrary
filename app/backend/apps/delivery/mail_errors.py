from smtplib import (
    SMTPAuthenticationError,
    SMTPDataError,
    SMTPException,
    SMTPNotSupportedError,
    SMTPRecipientsRefused,
    SMTPResponseException,
)
from ssl import SSLCertVerificationError

from apps.processing.jobs.execution_errors import ExecutionFailure
from apps.processing.jobs.failures import FailureKind


def response_failure(code: int, reason: str):
    return ExecutionFailure(
        FailureKind.TRANSIENT if 400 <= code < 500 else FailureKind.PERMANENT, reason
    )


def submission_failure(error: Exception):
    if isinstance(error, SMTPAuthenticationError):
        return ExecutionFailure(FailureKind.PERMANENT, "mail_authentication_failed")
    if isinstance(error, SMTPRecipientsRefused):
        responses = list(error.recipients.values())
        code = int(responses[0][0]) if responses else 550
        return response_failure(code, "recipient_rejected")
    if isinstance(error, SMTPDataError):
        return response_failure(error.smtp_code, "message_rejected")
    if isinstance(error, (SMTPNotSupportedError, SSLCertVerificationError)):
        return ExecutionFailure(FailureKind.PERMANENT, "mail_configuration_invalid")
    if isinstance(error, SMTPResponseException):
        return response_failure(error.smtp_code, "mail_server_rejected")
    return ExecutionFailure(FailureKind.UNCERTAIN, "mail_acceptance_unknown")


def connection_failure(error: Exception):
    failure = submission_failure(error)
    if failure.failure.kind == FailureKind.UNCERTAIN:
        return ExecutionFailure(FailureKind.TRANSIENT, "mail_connection_unavailable")
    return failure


MAIL_TRANSPORT_ERRORS = (SMTPException, OSError)
