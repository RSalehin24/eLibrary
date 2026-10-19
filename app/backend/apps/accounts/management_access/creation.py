from django.contrib.auth.hashers import check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.common.models import AuditLog
from apps.common.validation import reject_unknown_fields

from .policy import AccessConflict
from .queries import managed_account


class ManagedAccountCreateSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    email = serializers.EmailField(max_length=254)
    full_name = serializers.CharField(max_length=255, allow_blank=True, default="")
    password = serializers.CharField(
        min_length=12, max_length=4096, trim_whitespace=False, write_only=True
    )
    confirm_password = serializers.CharField(
        min_length=12, max_length=4096, trim_whitespace=False, write_only=True
    )
    totp_required = serializers.BooleanField(default=False)
    is_active = serializers.BooleanField(default=True)

    def validate(self, attrs):
        reject_unknown_fields(self)
        attrs["email"] = attrs["email"].lower()
        if attrs["password"] != attrs.pop("confirm_password"):
            raise ValidationError({"confirm_password": "The passwords do not match."})
        user = User(email=attrs["email"], full_name=attrs["full_name"])
        try:
            validate_password(attrs["password"], user)
        except DjangoValidationError as error:
            raise ValidationError({"password": error.messages}) from error
        return attrs


def previous_account(actor, identifier, values):
    receipt = AuditLog.objects.filter(pk=identifier).first()
    if receipt is None:
        return None
    if (
        receipt.actor_id != actor.pk
        or receipt.verb != "account.create"
        or receipt.target_type != User._meta.label_lower
    ):
        raise AccessConflict("This operation identifier belongs to another request.")
    target = managed_account(receipt.target_id)
    unchanged = all(
        getattr(target, field) == value
        for field, value in values.items()
        if field != "password"
    )
    if not unchanged or not check_password(values["password"], target.password):
        raise AccessConflict("This account or request changed. Refresh the list.")
    return target


def persist_account(actor, identifier, values):
    try:
        with transaction.atomic():
            target = User.objects.create_user(**values)
            AuditLog.objects.create(
                id=identifier,
                actor=actor,
                verb="account.create",
                target_type=target._meta.label_lower,
                target_id=str(target.pk),
            )
            return managed_account(target.pk)
    except IntegrityError as error:
        existing = previous_account(actor, identifier, values)
        if existing is not None:
            return existing
        raise AccessConflict(
            "An account was created concurrently. Refresh the list."
        ) from error


@transaction.atomic
def create_managed_account(actor, values):
    actor = User.objects.select_for_update(no_key=True).get(pk=actor.pk)
    if not actor.is_active or not actor.is_superuser:
        raise PermissionDenied(
            "Only a super administrator can set an initial password."
        )
    serializer = ManagedAccountCreateSerializer(data=values)
    serializer.is_valid(raise_exception=True)
    cleaned = dict(serializer.validated_data)
    identifier = cleaned.pop("operation_id")
    existing = previous_account(actor, identifier, cleaned)
    if existing is not None:
        return existing
    if User.objects.filter(email__iexact=cleaned["email"]).exists():
        raise ValidationError({"email": "An account already uses this email address."})
    return persist_account(actor, identifier, cleaned)
