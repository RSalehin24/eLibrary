from pathlib import Path

from rest_framework import serializers

from apps.catalog.models import ContributorRole, GeneratedAsset, GeneratedAssetStatus, GeneratedAssetType
from apps.common.text import clean_entity_display_text, normalize_catalog_text
from apps.common.permissions import user_can_download_book_assets, user_can_view_book_cover, user_can_view_preview_html
from apps.common.url_utils import public_api_url


def asset_exists(asset):
    if asset.file and asset.file.name:
        try:
            if asset.file.storage.exists(asset.file.name):
                return True
        except Exception:
            pass
        try:
            if Path(asset.file.path).exists():
                return True
        except (AttributeError, NotImplementedError, TypeError, ValueError):
            pass

    if asset.legacy_path:
        return Path(asset.legacy_path).exists()

    return False


def normalize_name_list(values):
    seen = set()
    normalized_values = []
    for raw_value in values or []:
        value = clean_entity_display_text(raw_value)
        if not value:
            continue
        normalized_key = normalize_catalog_text(value)
        if normalized_key in seen:
            continue
        seen.add(normalized_key)
        normalized_values.append(value)
    return normalized_values


class GeneratedAssetSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedAsset
        fields = [
            "id",
            "asset_type",
            "status",
            "content_type",
            "file_size",
            "download_url",
        ]

    def get_download_url(self, obj):
        request = self.context.get("request")
        if request is not None:
            if obj.asset_type == GeneratedAssetType.COVER:
                if not user_can_view_book_cover(request.user, obj.book):
                    return ""
            elif obj.asset_type == GeneratedAssetType.HTML:
                if not user_can_view_preview_html(request.user, obj.book):
                    return ""
            elif not user_can_download_book_assets(request.user, obj.book):
                return ""
        if not asset_exists(obj):
            return ""
        return public_api_url(
            "access-book-asset-download",
            kwargs={"slug": obj.book.slug, "asset_type": obj.asset_type},
            request=request,
        )


class EpubAssetReplaceSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        if Path(value.name).suffix.lower() != ".epub":
            raise serializers.ValidationError("Please upload an EPUB file.")
        return value


class MetadataContributorInputSerializer(serializers.Serializer):
    name = serializers.CharField()
    role = serializers.ChoiceField(choices=ContributorRole.choices)
