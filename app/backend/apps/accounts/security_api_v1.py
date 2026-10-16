from django_otp import login as otp_login
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.security_serializers import (
    DisableTOTPSerializer,
    ReauthenticationSerializer,
    SecurityTokenSerializer,
)
from apps.accounts.security_services import (
    cancel_totp_setup,
    confirm_totp_setup,
    disable_totp,
    start_totp_setup,
    totp_status,
)
from apps.accounts.serializers.totp import TOTPSetupSerializer, TOTPStatusSerializer
from apps.accounts.session_security import preserve_current_session
from apps.common.api import VersionedAPIView


class AccountTOTPStatusView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="account_totp_status", responses={200: TOTPStatusSerializer}
    )
    def get(self, request):
        return Response(totp_status(request.user))


class AccountTOTPSetupView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="account_totp_setup",
        request=ReauthenticationSerializer,
        responses={200: TOTPSetupSerializer},
    )
    def post(self, request):
        serializer = ReauthenticationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            start_totp_setup(
                request.user, serializer.validated_data["current_password"]
            )
        )


class AccountTOTPConfirmView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="account_totp_confirm",
        request=SecurityTokenSerializer,
        responses={204: None},
    )
    def post(self, request):
        serializer = SecurityTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = confirm_totp_setup(request.user, serializer.validated_data["token"])
        preserve_current_session(request)
        otp_login(request, device)
        return Response(status=204)


class AccountTOTPCancelView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="account_totp_cancel", request=None, responses={204: None}
    )
    def post(self, request):
        cancel_totp_setup(request.user)
        return Response(status=204)


class AccountTOTPDisableView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="account_totp_disable",
        request=DisableTOTPSerializer,
        responses={204: None},
    )
    def post(self, request):
        serializer = DisableTOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        disable_totp(request.user, serializer.validated_data)
        preserve_current_session(request)
        return Response(status=204)
