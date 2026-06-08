from rest_framework import serializers

from apps.access.models import PermissionGrant, SCOPED_PERMISSION_SCOPES, Bookmark, Highlight, ReadingSession
from apps.catalog.models import ContributorRole


class PermissionGrantSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)
    book_slug = serializers.CharField(source="book.slug", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)
    category_slug = serializers.CharField(source="category.slug", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    contributor_slug = serializers.CharField(source="contributor.slug", read_only=True)
    contributor_name = serializers.CharField(source="contributor.name", read_only=True)
    granted_by_email = serializers.EmailField(source="granted_by.email", read_only=True)
    target_type = serializers.SerializerMethodField()
    target_label = serializers.SerializerMethodField()

    class Meta:
        model = PermissionGrant
        fields = [
            "id",
            "user",
            "book",
            "category",
            "contributor",
            "scope",
            "is_active",
            "expires_at",
            "notes",
            "user_email",
            "book_slug",
            "book_title",
            "category_slug",
            "category_name",
            "contributor_slug",
            "contributor_name",
            "granted_by_email",
            "target_type",
            "target_label",
        ]

    def validate(self, attrs):
        book = attrs.get("book", getattr(self.instance, "book", None))
        category = attrs.get("category", getattr(self.instance, "category", None))
        contributor = attrs.get("contributor", getattr(self.instance, "contributor", None))
        selected_targets = [target for target in [book, category, contributor] if target is not None]

        if len(selected_targets) > 1:
            raise serializers.ValidationError("Choose only one target type per permission grant.")

        scope = attrs.get("scope", getattr(self.instance, "scope", ""))
        if selected_targets and scope not in {permission.value for permission in SCOPED_PERMISSION_SCOPES}:
            raise serializers.ValidationError("This permission can only be granted at the account level.")

        user = attrs.get("user", getattr(self.instance, "user", None))
        if user and scope in {"read:once", "read:durable"}:
            opposing_scope = "read:durable" if scope == "read:once" else "read:once"
            opposing_exists = PermissionGrant.objects.active_for_user(user).filter(
                scope=opposing_scope,
                book=book,
                category=category,
                contributor=contributor
            ).exists()
            if opposing_exists:
                raise serializers.ValidationError(
                    "Read Once and Durable Read permissions are mutually exclusive for the same target."
                )

        if contributor and not contributor.book_contributions.filter(role=ContributorRole.AUTHOR).exists():
            raise serializers.ValidationError({"contributor": "Only writers can be used for writer-specific access."})

        return attrs

    def get_target_type(self, obj):
        if obj.book_id:
            return "book"
        if obj.category_id:
            return "category"
        if obj.contributor_id:
            return "writer"
        return "account"

    def get_target_label(self, obj):
        if obj.book_id:
            return obj.book.title
        if obj.category_id:
            return obj.category.name
        if obj.contributor_id:
            return obj.contributor.name
        return "All books"


class ReadingSessionSerializer(serializers.ModelSerializer):
    book_slug = serializers.CharField(source="book.slug", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = ReadingSession
        fields = [
            "id",
            "book",
            "book_slug",
            "book_title",
            "last_location",
            "progress_percent",
            "last_opened_at",
        ]
        read_only_fields = ["book", "last_opened_at"]


class BookmarkSerializer(serializers.ModelSerializer):
    book_slug = serializers.CharField(source="book.slug", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = Bookmark
        fields = [
            "id",
            "book",
            "book_slug",
            "book_title",
            "location",
            "label",
            "note",
            "chapter_href",
            "chapter_label",
            "preview_text",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["book", "created_at", "updated_at"]


class HighlightSerializer(serializers.ModelSerializer):
    book_slug = serializers.CharField(source="book.slug", read_only=True)
    book_title = serializers.CharField(source="book.title", read_only=True)

    class Meta:
        model = Highlight
        fields = [
            "id",
            "book",
            "book_slug",
            "book_title",
            "cfi_range",
            "chapter_href",
            "chapter_label",
            "text",
            "note",
            "color",
            "kind",
            "tags",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["book", "created_at", "updated_at"]

    def validate_tags(self, value):
        if value in (None, ""):
            return []
        if not isinstance(value, list):
            raise serializers.ValidationError("Tags must be a list of strings.")
        cleaned = []
        for item in value:
            if not isinstance(item, str):
                raise serializers.ValidationError("Tags must be a list of strings.")
            trimmed = item.strip()
            if trimmed and trimmed not in cleaned:
                cleaned.append(trimmed)
        return cleaned
