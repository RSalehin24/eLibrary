import uuid
from pathlib import Path
from typing import ClassVar

from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import AbstractUser, PermissionsMixin
from django.db import models, transaction
from django.utils import timezone
from django.utils.crypto import salted_hmac

from apps.common.models import TimeStampedModel


class UserManager(BaseUserManager["User"]):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


def profile_image_upload_to(instance, filename):
    suffix = Path(filename or "").suffix.lower() or ".bin"
    return f"profile-images/{uuid.uuid4()}{suffix}"


class User(AbstractBaseUser, PermissionsMixin, TimeStampedModel):
    username = None
    first_name = models.CharField("first name", max_length=150, blank=True)
    last_name = models.CharField("last name", max_length=150, blank=True)
    is_staff = models.BooleanField(
        "staff status",
        default=False,
        help_text="Designates whether the user can log into this admin site.",
    )
    is_active = models.BooleanField(
        "active",
        default=True,
        help_text="Designates whether this user should be treated as active. Unselect this instead of deleting accounts.",
    )
    date_joined = models.DateTimeField("date joined", default=timezone.now)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255, blank=True)
    profile_image = models.FileField(upload_to=profile_image_upload_to, blank=True)
    kindle_emails = models.JSONField(default=list, blank=True)
    totp_required = models.BooleanField(default=False)
    email_setup_pending = models.BooleanField(default=False)
    password_setup_nonce = models.PositiveIntegerField(default=0)
    session_revision = models.PositiveIntegerField(default=0)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    objects: ClassVar[UserManager] = UserManager()
    get_full_name = AbstractUser.get_full_name
    get_short_name = AbstractUser.get_short_name
    email_user = AbstractUser.email_user

    class Meta:
        verbose_name = "user"
        verbose_name_plural = "users"
        abstract = False

    def clean(self):
        super().clean()
        self.email = type(self).objects.normalize_email(self.email)

    @transaction.atomic
    def save(self, *args, **kwargs):
        from apps.accounts.session_security import prepare_security_save

        prepare_security_save(self, kwargs)
        return super().save(*args, **kwargs)

    def session_hash(self, original, secret=None):
        if self.session_revision == 0:
            return original
        return salted_hmac(
            "apps.accounts.User.session_revision",
            f"{original}:{self.session_revision}",
            secret=secret,
            algorithm="sha256",
        ).hexdigest()

    def get_session_auth_hash(self):
        return self.session_hash(super().get_session_auth_hash())

    def get_session_auth_fallback_hash(self):
        for original, secret in zip(
            super().get_session_auth_fallback_hash(),
            settings.SECRET_KEY_FALLBACKS,
            strict=True,
        ):
            yield self.session_hash(original, secret)

    def __str__(self):
        return self.display_name or self.email

    @property
    def display_name(self):
        return self.full_name or self.email

    @property
    def has_totp_enabled(self):
        if hasattr(self, "has_totp_enabled_value"):
            return bool(self.has_totp_enabled_value)
        try:
            from django_otp.plugins.otp_totp.models import TOTPDevice
        except ImportError:
            return False

        return TOTPDevice.objects.filter(user=self, confirmed=True).exists()

    @property
    def requires_totp_setup(self):
        return self.totp_required and not self.has_totp_enabled

    @property
    def can_resend_setup_email(self):
        return self.is_active and self.email_setup_pending

    @property
    def global_grant_scopes(self):
        if self.is_superuser:
            return []

        prefetched_global_grants = getattr(
            self,
            "prefetched_active_global_grants",
            None,
        )
        if prefetched_global_grants is not None:
            return sorted({grant.scope for grant in prefetched_global_grants})

        from apps.access.models import PermissionGrant

        return sorted(
            set(
                PermissionGrant.objects.active_for_user(self)
                .filter(
                    book__isnull=True, category__isnull=True, contributor__isnull=True
                )
                .values_list("scope", flat=True)
            )
        )

    @property
    def capability_scopes(self):
        if self.is_superuser:
            return [
                "submit:create",
                "preview:html",
                "read:durable",
                "download:file",
                "metadata:edit",
                "physical_books:view",
                "processing:manage",
                "access:manage",
                "source_records:view",
                "admin:full_control",
                "send:kindle",
                "read:once",
            ]

        scopes = {"submit:create"}

        from apps.access.models import PermissionGrant

        active_grants = PermissionGrant.objects.active_for_user(self)
        scopes.update(active_grants.values_list("scope", flat=True))
        return sorted(scopes)
