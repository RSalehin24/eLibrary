import logging

from django.db import DatabaseError, transaction
from rest_framework.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.accounts.profile_services import ProfileConflict
from apps.common.images import normalized_uploaded_image

AVATAR_SIDE_PIXELS = 512
logger = logging.getLogger(__name__)


def profile_image_url(user):
    return (
        f"/api/v1/auth/profile/image/?revision={user.updated_at.timestamp()}"
        if user.profile_image
        else ""
    )


def normalized_profile_image(upload):
    return normalized_uploaded_image(upload, AVATAR_SIDE_PIXELS)


def remove_obsolete_image(storage, name):
    try:
        storage.delete(name)
    except OSError:
        logger.exception("Could not remove an obsolete profile image.")


@transaction.atomic
def replace_profile_image(actor, command):
    user = User.objects.select_for_update().get(pk=actor.pk)
    if not user.is_active:
        raise PermissionDenied("An active account is required.")
    if user.updated_at != command["expected_updated_at"]:
        raise ProfileConflict()
    old = user.profile_image.name
    storage = user.profile_image.storage
    persist_profile_image(user, command.get("image"))
    if old:
        transaction.on_commit(lambda: remove_obsolete_image(storage, old))
    return user


def persist_profile_image(user, image):
    if image is None:
        user.profile_image = ""
    else:
        user.profile_image.save(image.name, image, save=False)
    try:
        user.save(update_fields=["profile_image", "updated_at"])
    except (DatabaseError, OSError):
        if image is not None and user.profile_image.name:
            user.profile_image.storage.delete(user.profile_image.name)
        raise
