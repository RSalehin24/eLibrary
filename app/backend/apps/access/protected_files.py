from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.utils.http import content_disposition_header


def protected_storage_path(value):
    try:
        target = Path(value).resolve()
    except (OSError, TypeError, ValueError):
        raise Http404("Protected file is unavailable.") from None
    root = Path(settings.MEDIA_ROOT).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise Http404("Protected file is unavailable.")
    return target, target.relative_to(root).as_posix()


def protected_file_response(path, content_type=None):
    if not settings.PROTECTED_FILES_USE_NGINX:
        return FileResponse(Path(path).open("rb"), content_type=content_type)
    target, relative = protected_storage_path(path)
    response = HttpResponse(content_type=content_type or "application/octet-stream")
    response["X-Accel-Redirect"] = "/_protected/" + quote(relative, safe="/")
    response["Content-Length"] = target.stat().st_size
    response["X-Content-Type-Options"] = "nosniff"
    return response


def protected_download_response(asset, filename):
    from apps.access.storage import open_asset_stream

    if not settings.PROTECTED_FILES_USE_NGINX:
        return FileResponse(
            open_asset_stream(asset), as_attachment=True, filename=filename
        )
    path = asset.file.path if asset.file and asset.file.name else asset.legacy_path
    response = protected_file_response(path, "application/epub+zip")
    response["Content-Disposition"] = content_disposition_header(True, filename)
    return response
