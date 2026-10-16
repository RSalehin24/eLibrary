import logging
from email.utils import parseaddr
from smtplib import SMTPAuthenticationError

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import EmailMessage, get_connection
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.reading.launch import authorize_html_opening
from apps.accounts.kindle import validate_kindle_email_address
from apps.accounts.mail_configuration import (
    BREVO_EMAIL_BACKEND,
    BREVO_SMTP_PORT,
    DEFAULT_CONSOLE_EMAIL_BACKEND,
    SMTP_EMAIL_BACKEND,
    build_kindle_delivery_connection_attempts,
    build_kindle_delivery_connection_kwargs,
    resolve_kindle_delivery_email_backend,
)
from apps.catalog.models import Book, GeneratedAssetType, UserBookKindleSend
from apps.common.permissions import (
    user_can_download_book_assets,
    user_can_send_to_kindle,
    user_can_view_book_cover,
)

from .preview_html import html_asset_response
from .shared import (
    asset_download_filename,
    asset_is_available,
    missing_asset_response,
    open_asset_stream,
    read_asset_bytes,
    resolve_asset,
)

logger = logging.getLogger(__name__)


def valid_kindle_delivery_addresses(values):
    normalized = []
    for value in values:
        if not str(value or "").strip():
            continue
        try:
            normalized.append(validate_kindle_email_address(value))
        except DjangoValidationError:
            continue
    return normalized


def close_kindle_delivery_connection(connection, book_slug):
    if connection is None:
        return

    try:
        connection.close()
    except Exception:
        logger.exception(
            "Kindle delivery connection close failed for %s.",
            book_slug,
        )


class BookAssetDownloadView(APIView):
    permission_classes = (IsAuthenticated,)

    def get(self, request, slug, asset_type):
        book = get_object_or_404(Book, slug=slug)
        if asset_type == GeneratedAssetType.COVER:
            can_access = user_can_view_book_cover(request.user, book)
        elif asset_type == GeneratedAssetType.HTML:
            authorize_html_opening(request.user, book)
            can_access = True
        else:
            can_access = user_can_download_book_assets(request.user, book)

        if not can_access:
            raise PermissionDenied("You do not have download access for this book.")

        asset = resolve_asset(book, asset_type)
        if not asset_is_available(asset):
            return missing_asset_response(book, asset, actor=request.user)
        if asset.asset_type == GeneratedAssetType.HTML:
            return html_asset_response(book, asset)
        return FileResponse(
            open_asset_stream(asset),
            as_attachment=asset.asset_type != GeneratedAssetType.HTML,
            filename=asset_download_filename(book, asset),
        )


class BookSendToKindleView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request, slug):
        book = get_object_or_404(Book, slug=slug)
        if not user_can_send_to_kindle(request.user, book):
            raise PermissionDenied(
                "You do not have permission to send this book to Kindle."
            )

        kindle_emails = valid_kindle_delivery_addresses(
            request.user.kindle_emails or [],
        )
        if not kindle_emails:
            return Response(
                {
                    "detail": "Add at least one Kindle email in your profile before sending.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        asset = resolve_asset(book, GeneratedAssetType.EPUB)
        if not asset_is_available(asset):
            return missing_asset_response(book, asset, actor=request.user)

        attachment_bytes, _source_name, _path = read_asset_bytes(asset)
        filename = asset_download_filename(book, asset)
        raw_sender = (
            getattr(settings, "ACCOUNT_INVITE_FROM_EMAIL", "")
            or getattr(settings, "DEFAULT_FROM_EMAIL", "")
            or ""
        ).strip("'\" ")
        _name, sender = parseaddr(raw_sender)
        if not sender:
            sender = raw_sender
        connection_attempts = build_kindle_delivery_connection_attempts()
        connection_kwargs = connection_attempts[0]
        delivery_backend = connection_kwargs["backend"]
        delivered = []
        failed = []
        smtp_auth_failed = False

        smtp_host = str(connection_kwargs.get("host") or "").strip()
        smtp_username = str(connection_kwargs.get("username") or "").strip()
        smtp_password = str(connection_kwargs.get("password") or "").strip()
        if delivery_backend == SMTP_EMAIL_BACKEND and not (
            smtp_host and smtp_username and smtp_password
        ):
            return Response(
                {
                    "detail": (
                        "Kindle delivery requires SMTP because the Brevo API backend "
                        "does not support EPUB attachments. Configure EMAIL_HOST, "
                        "EMAIL_HOST_USER, and EMAIL_HOST_PASSWORD with the Brevo "
                        "SMTP login email and SMTP key from the SMTP page."
                    ),
                    "failedEmails": kindle_emails,
                    "senderEmail": sender,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        attempt_index = 0
        connection = get_connection(**connection_attempts[attempt_index])
        try:
            index = 0
            while index < len(kindle_emails):
                kindle_email = kindle_emails[index]
                message = EmailMessage(
                    subject=book.title,
                    body="",
                    from_email=sender,
                    to=[kindle_email],
                    connection=connection,
                )
                message.attach(filename, attachment_bytes, "application/epub+zip")
                try:
                    message.send(fail_silently=False)
                except SMTPAuthenticationError:
                    smtp_auth_failed = True
                    logger.exception(
                        "Kindle delivery authentication failed for %s to %s.",
                        book.slug,
                        kindle_email,
                    )
                    failed.extend(kindle_emails[index:])
                    break
                except Exception:
                    logger.exception(
                        "Kindle delivery failed for %s to %s.",
                        book.slug,
                        kindle_email,
                    )
                    failed.append(kindle_email)
                else:
                    delivered.append(kindle_email)
                index += 1
        finally:
            close_kindle_delivery_connection(connection, book.slug)

        if not delivered:
            detail = (
                "Kindle delivery could not authenticate with Brevo SMTP. "
                "Set EMAIL_HOST_USER to the Brevo SMTP login email and "
                "EMAIL_HOST_PASSWORD to an active SMTP key from Brevo's SMTP page. "
                "A Brevo API key will not work for SMTP."
                if smtp_auth_failed
                else (
                    "Kindle delivery failed for every configured address. "
                    "Check the outgoing mail settings and Amazon approved sender list."
                )
            )
            return Response(
                {
                    "detail": detail,
                    "failedEmails": failed,
                    "senderEmail": sender,
                },
                status=status.HTTP_502_BAD_GATEWAY,
            )

        UserBookKindleSend.objects.filter(user=request.user, book=book).delete()
        UserBookKindleSend.objects.create(user=request.user, book=book)

        detail = (
            f"Sent to {len(delivered)} Kindle email(s)."
            if not failed
            else (
                f"Sent to {len(delivered)} Kindle email(s). "
                f"{len(failed)} delivery attempt(s) failed."
            )
        )
        return Response(
            {
                "detail": detail,
                "deliveredEmails": delivered,
                "failedEmails": failed,
                "senderEmail": sender,
            }
        )


__all__ = [
    "BREVO_EMAIL_BACKEND",
    "BREVO_SMTP_PORT",
    "DEFAULT_CONSOLE_EMAIL_BACKEND",
    "SMTP_EMAIL_BACKEND",
    "BookAssetDownloadView",
    "BookSendToKindleView",
    "build_kindle_delivery_connection_kwargs",
    "resolve_kindle_delivery_email_backend",
]
