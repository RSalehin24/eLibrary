import mimetypes
import re
from pathlib import Path

from apps.catalog.models import GeneratedAssetType


def asset_source_name(asset):
    if asset.file and asset.file.name:
        return Path(asset.file.name).name
    if asset.legacy_path:
        return Path(asset.legacy_path).name
    return ""


def safe_download_stem(value):
    cleaned = re.sub(r'[<>:"/\\|?*]+', "-", str(value or "")).strip().strip(".")
    return cleaned or "book"


def asset_download_filename(book, asset):
    source_suffix = Path(asset_source_name(asset)).suffix.lower()
    if asset.asset_type == GeneratedAssetType.EPUB:
        suffix = ".epub"
    elif asset.asset_type == GeneratedAssetType.COVER:
        suffix = (
            source_suffix
            or mimetypes.guess_extension(asset.content_type or "")
            or ".jpg"
        )
    elif asset.asset_type == GeneratedAssetType.HTML:
        suffix = ".html"
    else:
        suffix = (
            source_suffix or mimetypes.guess_extension(asset.content_type or "") or ""
        )
    return f"{safe_download_stem(book.title)}{suffix}"
