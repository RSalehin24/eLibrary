from django.contrib.auth import login
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.accounts.password_link_serializers import (
    PasswordLinkConfirmationSerializer,
    PasswordLinkInspectionSerializer,
    PasswordLinkResultSerializer,
    PasswordLinkSerializer,
)
from apps.accounts.password_links import confirm_password_link, inspect_password_link
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.throttles import PasswordLinkRateThrottle


def require_anonymous_link_request(request):
    if request.user.is_authenticated:
        raise ValidationError({"session": "Sign out before using a password link."})


@method_decorator(csrf_protect, name="dispatch")
class PasswordLinkInspectView(VersionedAPIView):
    permission_classes = (AllowAny,)
    throttle_classes = (PasswordLinkRateThrottle,)

    @extend_schema(
        operation_id="password_link_inspect",
        request=PasswordLinkSerializer,
        responses={
            200: PasswordLinkInspectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            429: APIErrorSerializer,
            503: APIErrorSerializer,
        },
    )
    def post(self, request):
        require_anonymous_link_request(request)
        serializer = PasswordLinkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            PasswordLinkInspectionSerializer(
                inspect_password_link(serializer.validated_data)
            ).data
        )


@method_decorator(csrf_protect, name="dispatch")
class PasswordLinkConfirmView(VersionedAPIView):
    permission_classes = (AllowAny,)
    throttle_classes = (PasswordLinkRateThrottle,)

    @extend_schema(
        operation_id="password_link_confirm",
        request=PasswordLinkConfirmationSerializer,
        responses={
            200: PasswordLinkResultSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            429: APIErrorSerializer,
            503: APIErrorSerializer,
        },
    )
    def post(self, request):
        require_anonymous_link_request(request)
        serializer = PasswordLinkConfirmationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = confirm_password_link(serializer.validated_data)
        next_step = "login"
        if user.requires_totp_setup:
            login(request, user)
            next_step = "totp_setup"
        return Response(PasswordLinkResultSerializer({"next_step": next_step}).data)
