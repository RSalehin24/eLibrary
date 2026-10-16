from django.db.models import Exists, OuterRef
from rest_framework.exceptions import APIException, PermissionDenied

from apps.access.models import PermissionGrant, PermissionScope
from apps.accounts.models import User
from apps.common.permissions import user_has_scope


class AccessConflict(APIException):
    status_code = 409
    default_code = "state_conflict"
    default_detail = "The account or permission changed. Refresh before saving."


def require_access_manager(actor):
    if not actor.is_active or not user_has_scope(
        actor, [PermissionScope.ACCESS_MANAGE]
    ):
        raise PermissionDenied("Global access management is required.")


def account_is_editable(actor, target):
    if actor.pk == target.pk or target.is_superuser:
        return False
    privileged = target.is_staff or has_full_control(target)
    return actor.is_superuser or not privileged


def has_full_control(target):
    annotated = getattr(target, "has_full_control_value", None)
    if annotated is not None:
        return annotated
    return full_control_grants().filter(user=target).exists()


def full_control_grants():
    return PermissionGrant.objects.active().filter(
        scope=PermissionScope.ADMIN_FULL_CONTROL,
        book__isnull=True,
        category__isnull=True,
        contributor__isnull=True,
    )


def editable_accounts(actor):
    require_access_manager(actor)
    targets = User.objects.exclude(pk=actor.pk).filter(is_superuser=False)
    if actor.is_superuser:
        return targets
    return targets.annotate(
        has_full_control_value=Exists(
            full_control_grants().filter(user_id=OuterRef("pk"))
        )
    ).filter(is_staff=False, has_full_control_value=False)


def require_editable_account(actor, target):
    require_access_manager(actor)
    if not account_is_editable(actor, target):
        raise PermissionDenied(
            "This account must be managed by an authorized maintainer."
        )


def require_revision(instance, expected):
    if instance.updated_at != expected:
        raise AccessConflict()
