from django.conf import settings
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.db import transaction
from django.db.models import Case, Count, Exists, IntegerField, OuterRef, Prefetch, Q, Value, When
from django.db.models.functions import Lower
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import generics, status
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import (
    LoginSerializer,
    ManagedUserCreateSerializer,
    ManagedUserSerializer,
    ManagedUserUpdateSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    PasswordResetValidateSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    SessionSerializer,
    TOTPConfirmSerializer,
    TOTPSetupSerializer,
    TOTPStatusSerializer,
    UserSerializer,
)
from apps.accounts.serializers.support import send_account_setup_email
from apps.access.models import ACCOUNT_MANAGEABLE_PERMISSION_SCOPES, PermissionGrant
from apps.common.permissions import IsSuperAdmin
from apps.common.throttles import LoginRateThrottle, PasswordResetRateThrottle, RegisterRateThrottle


def extract_validation_error_message(detail):
    if isinstance(detail, ErrorDetail):
        return str(detail).strip()
    if isinstance(detail, str):
        return detail.strip()
    if isinstance(detail, (list, tuple)):
        for item in detail:
            message = extract_validation_error_message(item)
            if message:
                return message
        return ""
    if isinstance(detail, dict):
        for key in ("detail", "message", "non_field_errors"):
            if key in detail:
                message = extract_validation_error_message(detail[key])
                if message:
                    return message
        for key, value in detail.items():
            if key in {"detail", "message", "non_field_errors", "code"}:
                continue
            message = extract_validation_error_message(value)
            if message:
                return message
    return ""


def normalize_validation_error_detail(exc):
    return extract_validation_error_message(exc.detail) or "Request failed."


MANAGED_USER_DEFAULT_LIMIT = 60
MANAGED_USER_MAX_LIMIT = 180


def normalized_managed_user_status(value):
    normalized = str(value or "").strip().lower()
    if normalized in {"active", "disabled", "totp_required"}:
        return normalized
    return "all"


def clamped_query_int(value, *, default, minimum=0, maximum=None):
    try:
        parsed = int(str(value).strip() or default)
    except (TypeError, ValueError):
        parsed = default
    parsed = max(minimum, parsed)
    if maximum is not None:
        parsed = min(parsed, maximum)
    return parsed


def apply_managed_user_search(queryset, raw_query):
    query = str(raw_query or "").strip().lower()
    if not query:
        return queryset

    search_filter = Q(email__icontains=query) | Q(full_name__icontains=query)

    if "active".find(query) != -1:
        search_filter |= Q(is_active=True)
    if "disabled".find(query) != -1:
        search_filter |= Q(is_active=False)
    if "required".find(query) != -1:
        search_filter |= Q(totp_required=True)
    if "enabled".find(query) != -1:
        search_filter |= Q(has_totp_enabled_value=True, totp_required=False)
    if "optional".find(query) != -1:
        search_filter |= Q(has_totp_enabled_value=False, totp_required=False)

    matching_scopes = [
        scope.value
        for scope in ACCOUNT_MANAGEABLE_PERMISSION_SCOPES
        if query in scope.value.lower() or query in scope.label.lower()
    ]
    if matching_scopes:
        search_filter |= Q(
            permission_grants__scope__in=matching_scopes,
            permission_grants__is_active=True,
            permission_grants__book__isnull=True,
            permission_grants__category__isnull=True,
            permission_grants__contributor__isnull=True,
        )

    return queryset.filter(search_filter).distinct()


def ordered_managed_users_queryset(queryset, sort_key):
    if sort_key == "name_desc":
        return queryset.order_by(Lower("full_name").desc(), Lower("email").desc())
    if sort_key == "email_asc":
        return queryset.order_by(Lower("email"), Lower("full_name"))
    if sort_key == "email_desc":
        return queryset.order_by(Lower("email").desc(), Lower("full_name").desc())
    if sort_key == "status":
        return queryset.order_by(
            Case(
                When(is_active=True, then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            ),
            Lower("full_name"),
            Lower("email"),
        )
    return queryset.order_by(Lower("full_name"), Lower("email"))


class SessionView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        user = request.user if request.user.is_authenticated else None
        return Response(
            SessionSerializer({"authenticated": bool(user), "user": user}, context={"request": request}).data
        )


class RegisterView(generics.CreateAPIView):
    permission_classes = [IsAuthenticated, IsSuperAdmin]
    serializer_class = RegisterSerializer
    throttle_classes = [RegisterRateThrottle]


class DemoLoginView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        if request.user.is_authenticated:
            return Response(UserSerializer(request.user, context={"request": request}).data)

        User = get_user_model()
        email = settings.DEMO_USER_EMAIL
        password = settings.DEMO_USER_PASSWORD

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": "Demo User",
                "is_active": True,
                "totp_required": False,
            },
        )
        if created:
            user.set_password(password)
            user.save()

        login(request, user)
        return Response(UserSerializer(request.user, context={"request": request}).data)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            if isinstance(exc.detail, dict) and "code" in exc.detail and "detail" in exc.detail:
                code = exc.detail["code"]
                detail = exc.detail["detail"]
                if isinstance(code, (list, tuple)):
                    code = code[0]
                if isinstance(detail, (list, tuple)):
                    detail = detail[0]
                return Response({"detail": str(detail), "code": str(code)}, status=status.HTTP_400_BAD_REQUEST)
            raise
        login(request, serializer.validated_data["user"])
        return Response(UserSerializer(request.user, context={"request": request}).data)


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [PasswordResetRateThrottle]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data, context={"request": request})
        try:
            serializer.is_valid(raise_exception=True)
            serializer.save()
        except ValidationError as exc:
            detail = normalize_validation_error_detail(exc)
            status_code = (
                status.HTTP_404_NOT_FOUND
                if detail == "No user exist with this email."
                else status.HTTP_400_BAD_REQUEST
            )
            return Response({"detail": detail}, status=status_code)
        return Response({"detail": "Reset email has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        if request.user.is_authenticated:
            return Response(
                {"detail": "Please log out first before resetting a password from this link."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        serializer = PasswordResetConfirmSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            return Response(
                {"detail": normalize_validation_error_detail(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        user = serializer.save()
        if user.requires_totp_setup:
            login(request, user)
            return Response(
                {
                    "detail": "Password saved. Continue with two-factor setup.",
                    "next_step": "totp_setup",
                    "user": UserSerializer(
                        request.user, context={"request": request}
                    ).data,
                }
            )
        return Response({"detail": "Password reset complete.", "next_step": "login"})


class PasswordResetValidateView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = PasswordResetValidateSerializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
        except ValidationError as exc:
            return Response(
                {"detail": normalize_validation_error_detail(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"detail": "Password link is valid."})
