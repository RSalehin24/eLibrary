import io
import logging
import warnings
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import DatabaseError, transaction
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.accounts.profile_services import ProfileConflict

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 2048 * 2048
MAX_IMAGE_SIDE_PIXELS = 2048
AVATAR_SIDE_PIXELS = 512
logger = logging.getLogger(__name__)


def profile_image_url(user):
    return (
        f"/api/v1/auth/profile/image/?revision={user.updated_at.timestamp()}"
        if user.profile_image
        else ""
    )


def normalized_profile_image(upload):
    if upload.size > MAX_IMAGE_BYTES:
        raise ValidationError({"image": "Choose an image up to 5 MiB."})
    data = upload.read(MAX_IMAGE_BYTES + 1)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            return encode_avatar(data)
    except (
        UnidentifiedImageError,
        OSError,
        ValueError,
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
    ) as error:
        raise ValidationError(
            {
                "image": "Choose a valid, single-frame PNG, JPEG, or WebP image up to 2048×2048 pixels."
            }
        ) from error


def encode_avatar(data):
    with Image.open(io.BytesIO(data)) as source:
        if (
            source.format not in {"PNG", "JPEG", "WEBP"}
            or max(source.size) > MAX_IMAGE_SIDE_PIXELS
            or source.width * source.height > MAX_IMAGE_PIXELS
            or getattr(source, "is_animated", False)
        ):
            raise ValueError("Unsupported profile image.")
        source.load()
        image = ImageOps.exif_transpose(source).convert("RGBA")
        image.thumbnail((AVATAR_SIDE_PIXELS, AVATAR_SIDE_PIXELS))
        output = io.BytesIO()
        image.save(output, format="PNG")
    return ContentFile(output.getvalue(), name=f"{uuid4()}.png")


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
