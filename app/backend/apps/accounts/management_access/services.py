from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from apps.access.models import ACCOUNT_MANAGEABLE_PERMISSION_SCOPES, PermissionGrant
from apps.access.serializers import PermissionGrantSerializer
from apps.accounts.models import User
from apps.common.models import AuditLog

from .policy import AccessConflict, require_editable_account, require_revision
from .queries import account_grants, managed_account
from .serializers import (
    ManagedAccountUpdateSerializer,
    ManagedGrantCreateSerializer,
    ManagedGrantUpdateSerializer,
)


def locked_accounts(actor, identifier):
    accounts = {
        user.pk: user
        for user in User.objects.select_for_update(no_key=True)
        .filter(pk__in=(actor.pk, identifier))
        .order_by("pk")
    }
    target = (
        get_object_or_404(User, pk=identifier)
        if identifier not in accounts
        else accounts[identifier]
    )
    require_editable_account(accounts[actor.pk], target)
    return target


def record_change(actor, target, verb):
    AuditLog.objects.create(
        actor=actor,
        verb=verb,
        target_type=target._meta.label_lower,
        target_id=str(target.pk),
    )


def save_fields(instance, values):
    values.pop("expected_updated_at")
    for field, value in values.items():
        setattr(instance, field, value)
    instance.save(update_fields=[*values, "updated_at"])


@transaction.atomic
def update_managed_account(actor, identifier, values):
    target = locked_accounts(actor, identifier)
    serializer = ManagedAccountUpdateSerializer(data=values)
    serializer.is_valid(raise_exception=True)
    require_revision(target, serializer.validated_data["expected_updated_at"])
    save_fields(target, serializer.validated_data)
    record_change(actor, target, "account.update")
    return managed_account(identifier)


def matching_grants(values):
    return PermissionGrant.objects.active().filter(
        user=values["user"],
        scope=values["scope"],
        book=values.get("book"),
        category=values.get("category"),
        contributor=values.get("contributor"),
    )


def existing_grant(values):
    existing = PermissionGrant.objects.filter(pk=values["id"]).first()
    if existing is None:
        return None
    identity = (
        "user",
        "scope",
        "book",
        "category",
        "contributor",
        "expires_at",
        "notes",
    )
    if any(getattr(existing, field) != values.get(field) for field in identity):
        raise AccessConflict(
            "This request identifier belongs to a different permission."
        )
    return existing


def create_managed_grant(actor, identifier, values):
    return create_managed_grant_outcome(actor, identifier, values)[0]


@transaction.atomic
def create_managed_grant_outcome(actor, identifier, values):
    target = locked_accounts(actor, identifier)
    serializer = ManagedGrantCreateSerializer(data=values, context={"target": target})
    serializer.is_valid(raise_exception=True)
    cleaned = serializer.validated_data
    existing = existing_grant(cleaned)
    if existing is not None:
        return existing, False
    if matching_grants(cleaned).exists():
        raise AccessConflict("An active permission already exists for this target.")
    grant = persist_grant(actor, cleaned)
    return account_grants(target).get(pk=grant.pk), True


def persist_grant(actor, values):
    try:
        with transaction.atomic():
            grant = PermissionGrant.objects.create(**values, granted_by=actor)
            record_change(actor, grant, "permission.create")
            return grant
    except IntegrityError:
        existing = existing_grant(values)
        if existing is None:
            raise
        return existing


def validate_grant_update(grant, values):
    serializer = PermissionGrantSerializer(grant, data=values, partial=True)
    serializer.is_valid(raise_exception=True)
    identity = {
        field: getattr(grant, field)
        for field in ("user", "scope", "book", "category", "contributor")
    }
    if matching_grants(identity).exclude(pk=grant.pk).exists():
        raise AccessConflict("An active permission already exists for this target.")


@transaction.atomic
def update_managed_grant(actor, identifiers, values):
    account_id, grant_id = identifiers
    target = locked_accounts(actor, account_id)
    grant = get_object_or_404(
        PermissionGrant.objects.select_for_update(), pk=grant_id, user=target
    )
    if grant.scope not in ACCOUNT_MANAGEABLE_PERMISSION_SCOPES:
        raise ValidationError(
            {"scope": "This permission is managed through maintenance."}
        )
    serializer = ManagedGrantUpdateSerializer(data=values)
    serializer.is_valid(raise_exception=True)
    require_revision(grant, serializer.validated_data["expected_updated_at"])
    if serializer.validated_data.get("is_active", grant.is_active):
        validate_grant_update(grant, serializer.validated_data)
    save_fields(grant, serializer.validated_data)
    record_change(actor, grant, "permission.update")
    return account_grants(target).get(pk=grant.pk)
