from base64 import b32encode
from io import BytesIO
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.template import TemplateDoesNotExist, loader
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes
from django.utils.html import strip_tags
from django.utils.http import urlsafe_base64_encode
from rest_framework import serializers
from email.utils import parseaddr, formataddr

from apps.access.models import ACCOUNT_MANAGEABLE_PERMISSION_SCOPES, PermissionGrant
from apps.accounts.models import User


MANAGEABLE_PERMISSION_SCOPES = list(ACCOUNT_MANAGEABLE_PERMISSION_SCOPES)
MANAGEABLE_PERMISSION_SCOPE_VALUES = {
    scope.value for scope in ACCOUNT_MANAGEABLE_PERMISSION_SCOPES
}
LOCALHOST_HOSTS = {"localhost", "127.0.0.1"}


class PasswordLinkTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        login_timestamp = ""
        if user.last_login is not None:
            login_timestamp = user.last_login.replace(microsecond=0, tzinfo=None)
        email = getattr(user, user.get_email_field_name(), "") or ""
        return (
            f"{user.pk}{user.password}{login_timestamp}{timestamp}"
            f"{email}{user.password_setup_nonce}{int(user.email_setup_pending)}"
        )


password_link_token_generator = PasswordLinkTokenGenerator()


def build_qr_svg(data):
    try:
        import qrcode
        import qrcode.image.svg
    except ImportError:
        return ""

    image = qrcode.make(data, image_factory=qrcode.image.svg.SvgPathImage)
    buffer = BytesIO()
    image.save(buffer)
    return buffer.getvalue().decode("utf-8")


def sync_global_grants(user, scope_values, actor=None):
    cleaned_scopes = sorted(
        {scope for scope in scope_values if scope in MANAGEABLE_PERMISSION_SCOPE_VALUES}
    )
    PermissionGrant.objects.filter(
        user=user,
        book__isnull=True,
        category__isnull=True,
        contributor__isnull=True,
        scope__in=MANAGEABLE_PERMISSION_SCOPE_VALUES,
    ).exclude(scope__in=cleaned_scopes).delete()

    existing_scopes = set(
        PermissionGrant.objects.active_for_user(user)
        .filter(
            book__isnull=True,
            category__isnull=True,
            contributor__isnull=True,
            scope__in=MANAGEABLE_PERMISSION_SCOPE_VALUES,
        )
        .values_list("scope", flat=True)
    )
    for scope in cleaned_scopes:
        if scope in existing_scopes:
            continue
        PermissionGrant.objects.create(
            user=user,
            scope=scope,
            granted_by=actor,
            notes="Managed from the user administration workflow.",
        )


def normalize_frontend_base_url(base_url):
    normalized = (base_url or "").rstrip("/")
    if not normalized:
        return ""

    parsed = urlparse(normalized)
    hostname = (parsed.hostname or "").strip()
    frontend_port = str(getattr(settings, "FRONTEND_PORT", "") or "").strip()
    if hostname.lower() not in LOCALHOST_HOSTS or parsed.port or not frontend_port:
        return normalized

    if (parsed.scheme == "http" and frontend_port == "80") or (
        parsed.scheme == "https" and frontend_port == "443"
    ):
        return normalized

    credentials = ""
    if parsed.username:
        credentials = parsed.username
        if parsed.password:
            credentials = f"{credentials}:{parsed.password}"
        credentials = f"{credentials}@"

    updated = parsed._replace(netloc=f"{credentials}{hostname}:{frontend_port}")
    return urlunparse(updated).rstrip("/")


def format_duration_label(total_seconds):
    safe_total_seconds = max(1, int(total_seconds or 0))
    hours, remainder = divmod(safe_total_seconds, 3600)
    if hours and remainder == 0:
        unit = "hour" if hours == 1 else "hours"
        return f"{hours} {unit}"

    minutes = max(1, (safe_total_seconds + 59) // 60)
    unit = "minute" if minutes == 1 else "minutes"
    return f"{minutes} {unit}"


def send_link_email(
    user,
    *,
    request,
    subject_template_name,
    email_template_name,
    token_generator,
    frontend_path=None,
    extra_email_context=None,
):
    if user is None:
        return False

    use_https = request.is_secure() or settings.FRONTEND_BASE_URL.startswith("https://")
    protocol = "https" if use_https else "http"
    domain = request.get_host()
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_generator.make_token(user)

    configured_frontend_base_url = normalize_frontend_base_url(
        getattr(settings, "FRONTEND_BASE_URL", "") or ""
    )
    request_frontend_base_url = normalize_frontend_base_url(f"{protocol}://{domain}")
    frontend_base_url = configured_frontend_base_url or request_frontend_base_url
    frontend_site_name = urlparse(frontend_base_url).netloc or domain
    resolved_frontend_path = (
        str(frontend_path or settings.PASSWORD_RESET_FRONTEND_PATH or "").strip()
        or settings.PASSWORD_RESET_FRONTEND_PATH
    )

    reset_url = f"{frontend_base_url}{resolved_frontend_path}?uid={uid}&token={token}"
    email_context = {
        "email": user.email,
        "domain": frontend_site_name,
        "site_name": frontend_site_name,
        "uid": uid,
        "user": user,
        "token": token,
        "protocol": protocol,
        "frontend_reset_url": f"{frontend_base_url}{resolved_frontend_path}",
        "frontend_reset_full_url": reset_url,
        **(extra_email_context or {}),
    }

    subject = loader.render_to_string(subject_template_name, email_context)
    subject = " ".join(subject.splitlines()).strip()
    html_body = loader.render_to_string(email_template_name, email_context)
    text_template_name = f"{email_template_name.rsplit('.', 1)[0]}.txt"
    try:
        text_body = loader.render_to_string(text_template_name, email_context)
    except TemplateDoesNotExist:
        text_body = strip_tags(html_body)

    raw_from_email = (
        getattr(settings, "ACCOUNT_INVITE_FROM_EMAIL", "")
        or getattr(settings, "DEFAULT_FROM_EMAIL", "")
        or ""
    ).strip("'\" ")
    name, email = parseaddr(raw_from_email)
    if not name:
        name = "RSalehin24 Library"
    from_email = formataddr((name, email))

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email,
        to=[user.email],
    )
    message.attach_alternative(html_body, "text/html")
    delivered = message.send(fail_silently=False)
    if delivered < 1:
        raise RuntimeError("Invite email could not be delivered.")
    return True


def send_password_reset_email(
    email,
    *,
    request,
    subject_template_name,
    email_template_name,
    frontend_path=None,
    extra_email_context=None,
):
    user_model = get_user_model()
    user = (
        user_model._default_manager.filter(email__iexact=email, is_active=True)
        .order_by("pk")
        .first()
    )
    if user is None or user.email_setup_pending or not user.has_usable_password():
        return False

    email_context = dict(extra_email_context or {})
    email_context["reset_link_timeout_label"] = format_duration_label(
        getattr(settings, "PASSWORD_RESET_TIMEOUT", 0)
    )

    with transaction.atomic():
        locked_user = user_model._default_manager.select_for_update().get(pk=user.pk)
        locked_user.password_setup_nonce += 1
        locked_user.save(update_fields=["password_setup_nonce"])
        return send_link_email(
            locked_user,
            request=request,
            subject_template_name=subject_template_name,
            email_template_name=email_template_name,
            token_generator=password_link_token_generator,
            frontend_path=frontend_path,
            extra_email_context=email_context,
        )


def send_account_setup_email(user, *, request, invited_by=None):
    if user is None or not user.can_resend_setup_email:
        raise RuntimeError("Setup email is not available for this account.")

    with transaction.atomic():
        locked_user = User._default_manager.select_for_update().get(pk=user.pk)
        if not locked_user.can_resend_setup_email:
            raise RuntimeError("Setup email is not available for this account.")

        locked_user.password_setup_nonce += 1
        locked_user.save(update_fields=["password_setup_nonce"])
        send_link_email(
            locked_user,
            request=request,
            subject_template_name="registration/account_invite_subject.txt",
            email_template_name="registration/account_invite_email.html",
            token_generator=password_link_token_generator,
            frontend_path=settings.PASSWORD_CREATE_FRONTEND_PATH,
            extra_email_context={
                "invited_user": locked_user,
                "invited_by": invited_by,
            },
        )


def create_managed_user(validated_data, *, request):
    password = (validated_data.pop("password", "") or "").strip()
    send_invite_email = validated_data.pop("send_invite_email", True)
    global_scopes = validated_data.pop("global_scopes", [])

    with transaction.atomic():
        user = User.objects.create_user(
            password=None if send_invite_email else password or get_random_string(24),
            email_setup_pending=send_invite_email,
            **validated_data,
        )
        sync_global_grants(user, global_scopes, actor=request.user)
        if send_invite_email:
            try:
                send_account_setup_email(
                    user,
                    request=request,
                    invited_by=request.user,
                )
            except Exception as exc:
                raise serializers.ValidationError(
                    {
                        "send_invite_email": (
                            "Invite email could not be delivered. For Brevo, verify "
                            "BREVO_API_KEY and that ACCOUNT_INVITE_FROM_EMAIL/DEFAULT_FROM_EMAIL "
                            "is a verified sender."
                        )
                    }
                ) from exc
    return user
