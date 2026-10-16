from pathlib import Path

from django.http import Http404
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import serializers
from rest_framework.parsers import JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.protected_files import protected_file_response
from apps.accounts.profile_images import normalized_profile_image, replace_profile_image
from apps.accounts.profile_serializers import AccountProfileSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.validation import reject_unknown_fields


class ProfileImageCommandSerializer(serializers.Serializer):
    expected_updated_at = serializers.DateTimeField()

    def validate(self, attributes):
        reject_unknown_fields(self)
        return attributes


class ProfileImageUploadSerializer(ProfileImageCommandSerializer):
    image = serializers.FileField()

    def validate_image(self, value):
        return normalized_profile_image(value)


class AccountProfileImageView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)
    parser_classes = (MultiPartParser, JSONParser)

    @extend_schema(
        operation_id="profile_image",
        responses={200: OpenApiTypes.BINARY, 404: APIErrorSerializer},
    )
    def get(self, request):
        image = request.user.profile_image
        if not image or not image.storage.exists(image.name):
            raise Http404
        content_type = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }.get(Path(image.name).suffix.lower())
        if content_type is None:
            raise Http404
        response = protected_file_response(image.path, content_type)
        response["Content-Security-Policy"] = "default-src 'none'; sandbox"
        return response

    @extend_schema(
        operation_id="profile_image_upload",
        request=ProfileImageUploadSerializer,
        responses={
            200: AccountProfileSerializer,
            400: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def post(self, request):
        serializer = ProfileImageUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = replace_profile_image(request.user, serializer.validated_data)
        return Response(
            AccountProfileSerializer(user, context={"request": request}).data
        )

    @extend_schema(
        operation_id="profile_image_remove",
        request=ProfileImageCommandSerializer,
        responses={200: AccountProfileSerializer, 409: APIErrorSerializer},
    )
    def delete(self, request):
        serializer = ProfileImageCommandSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = replace_profile_image(request.user, serializer.validated_data)
        return Response(
            AccountProfileSerializer(user, context={"request": request}).data
        )
