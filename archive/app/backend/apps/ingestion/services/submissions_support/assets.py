import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files import File

from apps.catalog.models import GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType
from apps.common.models import LifecycleState, ReviewState
from apps.ingestion.pipeline.epub_properties.epub_builder import safe_epub_filename


def calculate_checksum(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def content_type_for_suffix(path):
    suffix = path.suffix.lower()
    if suffix == ".epub":
        return "application/epub+zip"
    if suffix in {".jpg", ".jpeg"}:
        return "image/jpeg"
    if suffix == ".webp":
        return "image/webp"
    if suffix == ".html":
        return "text/html"
    return "application/octet-stream"


def resolve_generated_cover_path(output_folder, requested_cover):
    if requested_cover:
        requested_path = Path(str(requested_cover))
        direct_path = requested_path if requested_path.is_absolute() else output_folder / requested_path
        if direct_path.exists():
            return direct_path

        requested_stem = requested_path.stem
        if requested_stem:
            for candidate in sorted(output_folder.glob(f"{requested_stem}.*")):
                if candidate.is_file():
                    return candidate

    for fallback_stem in ("book_cover", "book_image"):
        for candidate in sorted(output_folder.glob(f"{fallback_stem}.*")):
            if candidate.is_file():
                return candidate

    return None


def candidate_asset_paths(scraped_data):
    output_folder = Path(scraped_data["output_folder"])
    # Use the same sanitizer that EpubBuilder.build_epub uses so titles
    # containing path separators (e.g. "ভলিউম ৪/১") still resolve to the
    # file that was actually written to disk.
    epub_filename = safe_epub_filename(f"{scraped_data['book_title']}.epub")
    epub_path = output_folder / epub_filename
    if not epub_path.exists():
        epub_candidates = sorted(output_folder.glob("*.epub"))
        epub_path = epub_candidates[0] if epub_candidates else None

    cover_path = resolve_generated_cover_path(output_folder, scraped_data.get("cover", ""))
    return {
        GeneratedAssetType.HTML: output_folder / "book.html",
        GeneratedAssetType.EPUB: epub_path,
        GeneratedAssetType.COVER: cover_path,
    }


def path_is_within(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def cleanup_staged_asset_files(output_folder, synced_paths):
    if not output_folder:
        return

    output_folder = Path(output_folder)
    if not output_folder.exists() or not output_folder.is_dir():
        return

    media_root = Path(settings.MEDIA_ROOT)
    if path_is_within(output_folder, media_root):
        return

    for path in synced_paths:
        if path.exists() and path_is_within(path, output_folder):
            path.unlink()

    try:
        output_folder.rmdir()
    except OSError:
        pass


def sync_assets(book, job, scraped_data, *, generated_asset_labels, required_asset_types):
    synced_paths = []
    ready_asset_types = set()
    for asset_type, path in candidate_asset_paths(scraped_data).items():
        asset, _ = GeneratedAsset.objects.get_or_create(book=book, asset_type=asset_type)
        if not path or not Path(path).exists():
            asset.status = GeneratedAssetStatus.FAILED
            asset.save(update_fields=["status", "updated_at"])
            continue

        path = Path(path)
        asset.status = GeneratedAssetStatus.READY
        asset.legacy_path = str(path)
        asset.file_size = path.stat().st_size
        asset.content_type = content_type_for_suffix(path)
        asset.checksum = calculate_checksum(path)
        asset.source_job = job
        if asset.file and asset.file.name:
            asset.file.delete(save=False)
        with open(path, "rb") as handle:
            asset.file.save(path.name, File(handle), save=False)
        asset.storage_path = asset.file.name
        asset.legacy_path = ""
        asset.save(update_fields=["status", "legacy_path", "file_size", "content_type", "checksum", "source_job", "file", "storage_path", "updated_at"])
        synced_paths.append(path)
        ready_asset_types.add(asset_type)

    cleanup_staged_asset_files(scraped_data.get("output_folder"), synced_paths)

    missing_required_assets = [
        generated_asset_labels[asset_type]
        for asset_type in required_asset_types
        if asset_type not in ready_asset_types
    ]
    if missing_required_assets:
        book.state = LifecycleState.NEEDS_REVIEW
        book.review_state = ReviewState.NEEDS_REVIEW
        book.save(update_fields=["state", "review_state", "updated_at"])
        raise ValueError(f"Missing generated assets: {', '.join(missing_required_assets)}.")
