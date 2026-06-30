from uuid import uuid4

from rest_framework import serializers

from apps.catalog.models import Book, BookRecordType, ContributorRole, ManualBindingType, MetadataVersion
from apps.catalog.services import replace_book_relations
from apps.common.models import LifecycleState, ReviewState

from .common import MetadataContributorInputSerializer, normalize_name_list


class ManualBookCreateSerializer(serializers.Serializer):
    title = serializers.CharField()
    summary = serializers.CharField(required=False, allow_blank=True)
    writers = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    translators = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    compilers = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    editors = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    categories = serializers.ListField(child=serializers.CharField(), allow_empty=True)
    series = serializers.ListField(child=serializers.CharField(), required=False, allow_empty=True)
    is_compilation = serializers.BooleanField(required=False, default=False)
    binding = serializers.ChoiceField(choices=ManualBindingType.choices, required=False, allow_blank=True)
    publisher = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(required=False, allow_null=True, max_digits=10, decimal_places=2)

    def validate_title(self, value):
        title = value.strip()
        if not title:
            raise serializers.ValidationError("This field may not be blank.")
        return title

    def validate_writers(self, value):
        writers = normalize_name_list(value)
        if not writers:
            raise serializers.ValidationError("Add at least one writer.")
        return writers

    def validate_categories(self, value):
        categories = normalize_name_list(value)
        if not categories:
            raise serializers.ValidationError("Add at least one category.")
        return categories

    validate_translators = lambda self, value: normalize_name_list(value)
    validate_compilers = lambda self, value: normalize_name_list(value)
    validate_editors = lambda self, value: normalize_name_list(value)
    validate_series = lambda self, value: normalize_name_list(value)

    def create(self, validated_data):
        writer_names = validated_data.pop("writers", [])
        translator_names = validated_data.pop("translators", [])
        compiler_names = validated_data.pop("compilers", [])
        editor_names = validated_data.pop("editors", [])
        publisher_name = (validated_data.get("publisher") or "").strip()
        category_names = validated_data.pop("categories", [])
        series_names = validated_data.pop("series", [])
        book = Book.objects.create(
            title=validated_data["title"],
            summary=validated_data.get("summary", ""),
            state=LifecycleState.READY,
            review_state=ReviewState.APPROVED,
            record_type=BookRecordType.MANUAL,
            manual_is_compilation=validated_data.get("is_compilation", False),
            manual_binding=validated_data.get("binding", ""),
            manual_publisher=validated_data.get("publisher", ""),
            manual_price=validated_data.get("price"),
            source_site=f"manual-library:{uuid4().hex}",
            raw_scraped_metadata={"manual_entry": True},
            raw_scrape_payload={"manual_entry": True},
        )
        replace_book_relations(
            book,
            contributors=[
                *[{"name": name, "role": ContributorRole.AUTHOR} for name in writer_names],
                *[{"name": name, "role": ContributorRole.TRANSLATOR} for name in translator_names],
                *[{"name": name, "role": ContributorRole.EDITOR} for name in [*compiler_names, *editor_names]],
                *([{"name": publisher_name, "role": ContributorRole.PUBLISHER}] if publisher_name else []),
            ],
            series_names=series_names,
            category_names=category_names,
        )
        return book


class BookMetadataUpdateSerializer(serializers.ModelSerializer):
    contributors = MetadataContributorInputSerializer(many=True, required=False)
    series = serializers.ListField(child=serializers.CharField(), required=False)
    categories = serializers.ListField(child=serializers.CharField(), required=False)
    notes = serializers.CharField(required=False, allow_blank=True, write_only=True)
    price = serializers.DecimalField(source="manual_price", required=False, allow_null=True, max_digits=10, decimal_places=2)
    binding = serializers.ChoiceField(source="manual_binding", choices=ManualBindingType.choices, required=False, allow_blank=True)
    is_compilation = serializers.BooleanField(source="manual_is_compilation", required=False)
    publisher = serializers.CharField(source="manual_publisher", required=False, allow_blank=True)

    class Meta:
        model = Book
        fields = [
            "title",
            "summary",
            "state",
            "review_state",
            "book_info_html",
            "dedication_html",
            "main_content_html",
            "toc",
            "contributors",
            "series",
            "categories",
            "notes",
            "price",
            "binding",
            "is_compilation",
            "publisher",
        ]

    def snapshot(self, instance):
        return {
            "title": instance.title,
            "summary": instance.summary,
            "state": instance.state,
            "review_state": instance.review_state,
            "book_info_html": instance.book_info_html,
            "dedication_html": instance.dedication_html,
            "main_content_html": instance.main_content_html,
            "toc": instance.toc,
            "contributors": [
                {"name": relation.contributor.name, "role": relation.role}
                for relation in instance.book_contributors.all()
            ],
            "series": [relation.series.name for relation in instance.book_series.all()],
            "categories": [relation.category.name for relation in instance.book_categories.all()],
            "price": str(instance.manual_price) if instance.manual_price else None,
            "binding": instance.manual_binding,
            "is_compilation": instance.manual_is_compilation,
            "publisher": instance.manual_publisher,
        }

    def update(self, instance, validated_data):
        notes = validated_data.pop("notes", "")
        contributors = validated_data.pop("contributors", None)
        series = validated_data.pop("series", None)
        categories = validated_data.pop("categories", None)
        actor = self.context["request"].user

        MetadataVersion.objects.create(
            book=instance,
            snapshot=self.snapshot(instance),
            source="manual_edit_before",
            notes=notes,
            created_by=actor,
        )
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        replace_book_relations(
            instance,
            contributors=contributors,
            series_names=series,
            category_names=categories,
        )
        MetadataVersion.objects.create(
            book=instance,
            snapshot=self.snapshot(instance),
            source="manual_edit_after",
            notes=notes,
            created_by=actor,
        )
        return instance
