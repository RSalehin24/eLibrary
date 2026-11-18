from django.http import HttpResponse

from apps.access.services.preview_html import (
    normalize_preview_book_sections,
    normalize_preview_html,
)


def html_asset_response(book, asset):
    html = normalize_preview_html(book, asset)
    return HttpResponse(html, content_type=asset.content_type or "text/html")


__all__ = [
    "html_asset_response",
    "normalize_preview_book_sections",
    "normalize_preview_html",
]
