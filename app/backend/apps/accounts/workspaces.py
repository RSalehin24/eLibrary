from apps.access.models import PermissionGrant, PermissionScope
from apps.common.permissions import (
    is_book_administrator,
    user_can_create_catalog_book,
    user_has_scope,
)

MANAGEMENT_SECTIONS = (
    ("sources", PermissionScope.PROCESSING_MANAGE),
    ("books", PermissionScope.METADATA_EDIT),
    ("jobs", PermissionScope.PROCESSING_MANAGE),
    ("automations", PermissionScope.PROCESSING_MANAGE),
    ("users-access", PermissionScope.ACCESS_MANAGE),
)


def management_sections(user):
    if not getattr(user, "is_authenticated", False) or not user.is_active:
        return []
    allowed = {
        name for name, scope in MANAGEMENT_SECTIONS if user_has_scope(user, [scope])
    }
    if (
        "books" not in allowed
        and PermissionGrant.objects.active_for_user(user)
        .filter(
            scope=PermissionScope.METADATA_EDIT,
        )
        .exists()
    ):
        allowed.add("books")
    sections = [name for name, _scope in MANAGEMENT_SECTIONS if name in allowed]
    return ["overview", *sections] if sections else []


def available_workspaces(user):
    sections = management_sections(user)
    return {
        "reader": True,
        "manage": bool(sections),
        "management_sections": sections,
        "can_create_books": user_can_create_catalog_book(user),
        "can_edit_books": is_book_administrator(user),
    }
