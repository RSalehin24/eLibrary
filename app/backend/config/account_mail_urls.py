from apps.accounts.link_mail.api import (
    AccountMailOperationsView,
    AccountMailOperationView,
    ManagedInvitationResendView,
    ManagedInvitationView,
    PasswordResetRequestView,
)
from django.urls import path

account_mail_routes = [
    path(
        "auth/password-reset/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "manage/invitations/",
        ManagedInvitationView.as_view(),
        name="managed-invitation",
    ),
    path(
        "manage/users/<int:identifier>/invitation/",
        ManagedInvitationResendView.as_view(),
        name="managed-invitation-resend",
    ),
    path(
        "manage/users/<int:identifier>/mail/",
        AccountMailOperationsView.as_view(),
        name="account-mail-operations",
    ),
    path(
        "manage/mail/<uuid:identifier>/",
        AccountMailOperationView.as_view(),
        name="account-mail-operation",
    ),
]
