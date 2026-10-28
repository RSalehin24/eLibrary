import io
import warnings
from uuid import uuid4

from django.core.files.base import ContentFile
from PIL import Image, ImageOps, UnidentifiedImageError
from rest_framework.exceptions import ValidationError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_PIXELS = 2048 * 2048
MAX_IMAGE_SIDE_PIXELS = 2048


def normalized_uploaded_image(upload, output_side):
    if upload.size is None or upload.size > MAX_IMAGE_BYTES:
        raise ValidationError({"image": "Choose an image up to 5 MiB."})
    data = upload.read(MAX_IMAGE_BYTES + 1)
    if len(data) > MAX_IMAGE_BYTES:
        raise ValidationError({"image": "Choose an image up to 5 MiB."})
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            return encode_image(data, output_side)
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


def encode_image(data, output_side):
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
        image.thumbnail((output_side, output_side))
        output = io.BytesIO()
        image.save(output, format="PNG")
    return ContentFile(output.getvalue(), name=f"{uuid4()}.png")
