from django.urls import path

from apps.accounts.views import (
    DemoLoginView,
    LoginView,
    LogoutView,
    ManagedUserDetailView,
    ManagedUserListCreateView,
    ManagedUserResendSetupEmailView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    PasswordResetValidateView,
    ProfileView,
    SessionView,
    TOTPConfirmView,
    TOTPCancelSetupView,
    TOTPDisableView,
    TOTPSetupView,
    TOTPStatusView,
)


urlpatterns = [
    path("session/", SessionView.as_view(), name="auth-session"),
    path("demo-login/", DemoLoginView.as_view(), name="auth-demo-login"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("profile/", ProfileView.as_view(), name="auth-profile"),
    path("password-reset/", PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path("password-reset/validate/", PasswordResetValidateView.as_view(), name="auth-password-reset-validate"),
    path("password-reset/confirm/", PasswordResetConfirmView.as_view(), name="auth-password-reset-confirm"),
    path("users/", ManagedUserListCreateView.as_view(), name="auth-user-list"),
    path("users/<int:pk>/", ManagedUserDetailView.as_view(), name="auth-user-detail"),
    path("users/<int:pk>/resend-setup-email/", ManagedUserResendSetupEmailView.as_view(), name="auth-user-resend-setup-email"),
    path("2fa/status/", TOTPStatusView.as_view(), name="auth-2fa-status"),
    path("2fa/setup/", TOTPSetupView.as_view(), name="auth-2fa-setup"),
    path("2fa/confirm/", TOTPConfirmView.as_view(), name="auth-2fa-confirm"),
    path("2fa/cancel/", TOTPCancelSetupView.as_view(), name="auth-2fa-cancel"),
    path("2fa/disable/", TOTPDisableView.as_view(), name="auth-2fa-disable"),
]
