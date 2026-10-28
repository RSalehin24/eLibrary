from rest_framework import serializers

from apps.accounts.serializers import UserSerializer


class WorkspaceUserSerializer(UserSerializer):
    def get_profile_image_url(self, user) -> str:
        from apps.accounts.profile_images import profile_image_url

        return profile_image_url(user)


class WorkspaceAccessSerializer(serializers.Serializer):
    reader = serializers.BooleanField()
    manage = serializers.BooleanField()
    management_sections = serializers.ListField(child=serializers.CharField())
    can_create_books = serializers.BooleanField()
    can_edit_books = serializers.BooleanField()


class WorkspaceSessionSerializer(serializers.Serializer):
    authenticated = serializers.BooleanField()
    user = WorkspaceUserSerializer(allow_null=True)
    workspaces = WorkspaceAccessSerializer()
    csrf_token = serializers.CharField()
