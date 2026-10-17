import logging
from pathlib import Path

from django.http import Http404

logger = logging.getLogger(__name__)


def asset_file_exists(file_field):
    if not file_field or not getattr(file_field, "name", ""):
        return False
    storage = getattr(file_field, "storage", None)
    if storage is not None:
        try:
            if storage.exists(file_field.name):
                return True
        except OSError:
            logger.warning("Asset storage verification failed.", exc_info=True)
    try:
        return Path(file_field.path).exists()
    except (AttributeError, NotImplementedError, TypeError, ValueError):
        return False


def open_asset_stream(asset):
    if asset.file and asset.file.name and asset_file_exists(asset.file):
        asset.file.open("rb")
        return asset.file
    if asset.legacy_path:
        legacy_path = Path(asset.legacy_path)
        if legacy_path.exists():
            return legacy_path.open("rb")
    raise Http404("Asset file is not available.")


def asset_is_available(asset):
    if asset is None:
        return False
    if asset.file and asset.file.name and asset_file_exists(asset.file):
        return True
    return bool(asset.legacy_path and Path(asset.legacy_path).is_file())
