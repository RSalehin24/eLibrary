from django.core.management.base import BaseCommand, CommandError

from apps.access.reading.epub_paths import InvalidEpub
from apps.access.reading.preparation import prepare_epub_asset
from apps.catalog.models import GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType


class Command(BaseCommand):
    help = "Validate and prepare existing EPUB resources outside reader requests."

    def add_arguments(self, parser):
        parser.add_argument("--asset", required=True, help="Generated EPUB asset UUID")

    def handle(self, *args, **options):
        asset = GeneratedAsset.objects.filter(
            pk=options["asset"],
            asset_type=GeneratedAssetType.EPUB,
            status=GeneratedAssetStatus.READY,
        ).first()
        if asset is None:
            raise CommandError("Ready EPUB asset not found.")
        try:
            publication = prepare_epub_asset(asset)
        except InvalidEpub as exc:
            raise CommandError(str(exc)) from exc
        self.stdout.write(f"Prepared publication {publication.pk}")
