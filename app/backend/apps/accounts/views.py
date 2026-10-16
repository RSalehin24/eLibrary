"""Compatibility exports backed by regular Python modules."""

from django.conf import settings
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.db import transaction
from django.db.models import (
    Case,
    Count,
    Exists,
    IntegerField,
    OuterRef,
    Prefetch,
    Q,
    Value,
    When,
)
from django.db.models.functions import Lower
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import generics, status
from rest_framework.exceptions import ErrorDetail, ValidationError
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.models import ACCOUNT_MANAGEABLE_PERMISSION_SCOPES, PermissionGrant
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
from apps.common.permissions import IsSuperAdmin
from apps.common.throttles import (
    LoginRateThrottle,
    PasswordResetRateThrottle,
    RegisterRateThrottle,
)

from .view_modules.auth_and_password_views import (
    MANAGED_USER_DEFAULT_LIMIT,
    MANAGED_USER_MAX_LIMIT,
    DemoLoginView,
    LoginView,
    LogoutView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetValidateView,
    RegisterView,
    SessionView,
    apply_managed_user_search,
    clamped_query_int,
    extract_validation_error_message,
    normalize_validation_error_detail,
    normalized_managed_user_status,
    ordered_managed_users_queryset,
)
from .view_modules.totp_profile_managed_user_views import (
    ManagedUserDetailView,
    ManagedUserListCreateView,
    ManagedUserResendSetupEmailView,
    ProfileView,
    TOTPCancelSetupView,
    TOTPConfirmView,
    TOTPDisableView,
    TOTPSetupView,
    TOTPStatusView,
)

__all__ = [
    "ACCOUNT_MANAGEABLE_PERMISSION_SCOPES",
    "MANAGED_USER_DEFAULT_LIMIT",
    "MANAGED_USER_MAX_LIMIT",
    "APIView",
    "AllowAny",
    "Case",
    "Count",
    "DemoLoginView",
    "ErrorDetail",
    "Exists",
    "FormParser",
    "IntegerField",
    "IsAuthenticated",
    "IsSuperAdmin",
    "JSONParser",
    "LoginRateThrottle",
    "LoginSerializer",
    "LoginView",
    "LogoutView",
    "Lower",
    "ManagedUserCreateSerializer",
    "ManagedUserDetailView",
    "ManagedUserListCreateView",
    "ManagedUserResendSetupEmailView",
    "ManagedUserSerializer",
    "ManagedUserUpdateSerializer",
    "MultiPartParser",
    "OuterRef",
    "PasswordResetConfirmSerializer",
    "PasswordResetConfirmView",
    "PasswordResetRateThrottle",
    "PasswordResetRequestSerializer",
    "PasswordResetRequestView",
    "PasswordResetValidateSerializer",
    "PasswordResetValidateView",
    "PermissionGrant",
    "Prefetch",
    "ProfileSerializer",
    "ProfileUpdateSerializer",
    "ProfileView",
    "Q",
    "RegisterRateThrottle",
    "RegisterSerializer",
    "RegisterView",
    "Response",
    "SessionSerializer",
    "SessionView",
    "TOTPCancelSetupView",
    "TOTPConfirmSerializer",
    "TOTPConfirmView",
    "TOTPDevice",
    "TOTPDisableView",
    "TOTPSetupSerializer",
    "TOTPSetupView",
    "TOTPStatusSerializer",
    "TOTPStatusView",
    "UserSerializer",
    "ValidationError",
    "Value",
    "When",
    "apply_managed_user_search",
    "clamped_query_int",
    "extract_validation_error_message",
    "generics",
    "get_user_model",
    "login",
    "logout",
    "normalize_validation_error_detail",
    "normalized_managed_user_status",
    "ordered_managed_users_queryset",
    "send_account_setup_email",
    "settings",
    "status",
    "transaction",
    "update_session_auth_hash",
]
