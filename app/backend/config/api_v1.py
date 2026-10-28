from apps.access.views.personal_annotations import (
    PersonalBookmarkDetailView,
    PersonalBookmarksView,
    PersonalHighlightDetailView,
    PersonalHighlightsView,
)
from apps.access.views.reader_access import ReaderAccessView, ReaderDownloadView
from apps.access.views.reader_annotations import (
    ReaderBookmarkDetailView,
    ReaderBookmarksView,
    ReaderHighlightDetailView,
    ReaderHighlightsView,
)
from apps.access.views.reader_v1 import (
    ReaderLaunchView,
    ReaderProgressView,
    ReaderResourceView,
    ReaderSessionView,
)
from apps.accounts.api_v1 import WorkspaceSessionView
from apps.accounts.auth_api_v1 import WorkspaceLoginView, WorkspaceLogoutView
from apps.accounts.management_access.api import (
    AccessReferencesView,
    ManagedAccountDetailView,
    ManagedAccountGrantDetailView,
    ManagedAccountGrantListView,
    ManagedAccountListView,
)
from apps.accounts.password_link_api_v1 import (
    PasswordLinkConfirmView,
    PasswordLinkInspectView,
)
from apps.accounts.profile_api_v1 import AccountProfileView
from apps.accounts.security_api_v1 import (
    AccountTOTPCancelView,
    AccountTOTPConfirmView,
    AccountTOTPDisableView,
    AccountTOTPSetupView,
    AccountTOTPStatusView,
)
from apps.catalog.views.collections import PublicCollectionsView
from apps.catalog.views.editorial import ManagedBookDetailView, WithdrawBookView
from apps.catalog.views.entities import PublicEntityDetailView
from apps.catalog.views.library import MyBookDetailView, MyBooksView
from apps.catalog.views.management import ManagedBookListView
from apps.catalog.views.public import PublicBookDetailView, PublicBookListView
from apps.catalog.views.sitemaps import SitemapEntriesView, SitemapIndexView
from apps.delivery.api_v1 import (
    KindleBookView,
    KindleOperationsView,
    KindleOperationView,
)
from apps.ingestion.source_workspace.api import (
    SourceEntryDetailView,
    SourceEntryListView,
)
from apps.processing.api_v1 import (
    BackgroundJobDetailView,
    BackgroundJobListView,
    PrepareAssetView,
    ProcessingAssetListView,
)
from apps.processing.managed_assets import ManagedAssetDownloadView
from apps.processing.overview.api import ManagementOverviewView, OverviewWorkView
from django.urls import path

from config.account_mail_urls import account_mail_routes
from config.automation_urls import automation_routes
from config.book_control_urls import book_control_routes
from config.catalog_creation_urls import catalog_creation_routes
from config.catalog_entity_urls import catalog_entity_routes
from config.health_urls import health_routes
from config.personal_library_urls import personal_library_routes
from config.reader_file_urls import reader_file_routes
from config.source_processing_urls import urlpatterns as source_processing_routes

app_name = "api_v1"
urlpatterns = [
    *health_routes,
    *reader_file_routes,
    *personal_library_routes,
    *catalog_creation_routes,
    *catalog_entity_routes,
    *automation_routes,
    *source_processing_routes,
    path(
        "manage/overview/", ManagementOverviewView.as_view(), name="management-overview"
    ),
    path(
        "manage/overview/work/",
        OverviewWorkView.as_view(),
        name="management-overview-work",
    ),
    *account_mail_routes,
    path("manage/sources/", SourceEntryListView.as_view(), name="managed-sources"),
    path(
        "manage/sources/<uuid:identifier>/",
        SourceEntryDetailView.as_view(),
        name="managed-source",
    ),
    path(
        "auth/password-links/inspect/",
        PasswordLinkInspectView.as_view(),
        name="password-link-inspect",
    ),
    path(
        "auth/password-links/confirm/",
        PasswordLinkConfirmView.as_view(),
        name="password-link-confirm",
    ),
    path("manage/users/", ManagedAccountListView.as_view(), name="managed-accounts"),
    path(
        "manage/users/<int:identifier>/",
        ManagedAccountDetailView.as_view(),
        name="managed-account",
    ),
    path(
        "manage/users/<int:identifier>/grants/",
        ManagedAccountGrantListView.as_view(),
        name="managed-account-grants",
    ),
    path(
        "manage/users/<int:identifier>/grants/<uuid:grant_id>/",
        ManagedAccountGrantDetailView.as_view(),
        name="managed-account-grant",
    ),
    path(
        "manage/access/references/",
        AccessReferencesView.as_view(),
        name="access-references",
    ),
    path(
        "delivery/books/<str:slug>/kindle/",
        KindleBookView.as_view(),
        name="kindle-book",
    ),
    path(
        "delivery/operations/<uuid:identifier>/",
        KindleOperationView.as_view(),
        name="kindle-operation",
    ),
    path("me/kindle/", KindleOperationsView.as_view(), name="kindle-operations"),
    path("auth/session/", WorkspaceSessionView.as_view(), name="auth-session"),
    path("auth/login/", WorkspaceLoginView.as_view(), name="auth-login"),
    path("auth/logout/", WorkspaceLogoutView.as_view(), name="auth-logout"),
    path("auth/profile/", AccountProfileView.as_view(), name="account-profile"),
    path(
        "auth/2fa/status/", AccountTOTPStatusView.as_view(), name="account-totp-status"
    ),
    path("auth/2fa/setup/", AccountTOTPSetupView.as_view(), name="account-totp-setup"),
    path(
        "auth/2fa/confirm/",
        AccountTOTPConfirmView.as_view(),
        name="account-totp-confirm",
    ),
    path(
        "auth/2fa/cancel/", AccountTOTPCancelView.as_view(), name="account-totp-cancel"
    ),
    path(
        "auth/2fa/disable/",
        AccountTOTPDisableView.as_view(),
        name="account-totp-disable",
    ),
    path("catalog/books/", PublicBookListView.as_view(), name="public-book-list"),
    path(
        "catalog/collections/",
        PublicCollectionsView.as_view(),
        name="public-collections",
    ),
    path("catalog/sitemaps/", SitemapIndexView.as_view(), name="sitemap-index"),
    path(
        "catalog/sitemaps/<str:kind>/<int:page>/",
        SitemapEntriesView.as_view(),
        name="sitemap-entries",
    ),
    path(
        "catalog/entities/<str:kind>/<str:slug>/",
        PublicEntityDetailView.as_view(),
        name="public-entity-detail",
    ),
    path(
        "catalog/books/<path:slug>/",
        PublicBookDetailView.as_view(),
        name="public-book-detail",
    ),
    path("manage/books/", ManagedBookListView.as_view(), name="managed-book-list"),
    path("manage/jobs/", BackgroundJobListView.as_view(), name="managed-job-list"),
    path(
        "manage/jobs/<uuid:identifier>/",
        BackgroundJobDetailView.as_view(),
        name="managed-job-detail",
    ),
    path(
        "manage/assets/<uuid:identifier>/prepare/",
        PrepareAssetView.as_view(),
        name="managed-asset-prepare",
    ),
    path(
        "manage/assets/<uuid:identifier>/download/",
        ManagedAssetDownloadView.as_view(),
        name="managed-asset-download",
    ),
    path(
        "manage/books/<str:slug>/assets/",
        ProcessingAssetListView.as_view(),
        name="managed-book-assets",
    ),
    path(
        "manage/books/<str:slug>/",
        ManagedBookDetailView.as_view(),
        name="managed-book-detail",
    ),
    *book_control_routes,
    path(
        "manage/books/<str:slug>/withdraw/",
        WithdrawBookView.as_view(),
        name="managed-book-withdraw",
    ),
    path("me/books/", MyBooksView.as_view(), name="my-books"),
    path("me/bookmarks/", PersonalBookmarksView.as_view(), name="personal-bookmarks"),
    path(
        "me/bookmarks/<uuid:annotation_id>/",
        PersonalBookmarkDetailView.as_view(),
        name="personal-bookmark-detail",
    ),
    path(
        "me/highlights/", PersonalHighlightsView.as_view(), name="personal-highlights"
    ),
    path(
        "me/highlights/<uuid:annotation_id>/",
        PersonalHighlightDetailView.as_view(),
        name="personal-highlight-detail",
    ),
    path("me/books/<path:slug>/", MyBookDetailView.as_view(), name="my-book-detail"),
    path(
        "reading/books/<str:slug>/access/",
        ReaderAccessView.as_view(),
        name="reader-access",
    ),
    path(
        "reading/books/<str:slug>/download/",
        ReaderDownloadView.as_view(),
        name="reader-download",
    ),
    path(
        "reading/books/<str:slug>/launch/",
        ReaderLaunchView.as_view(),
        name="reader-launch",
    ),
    path(
        "reading/sessions/<uuid:identifier>/",
        ReaderSessionView.as_view(),
        name="reader-session",
    ),
    path(
        "reading/sessions/<uuid:identifier>/progress/",
        ReaderProgressView.as_view(),
        name="reader-progress",
    ),
    path(
        "reading/sessions/<uuid:identifier>/bookmarks/",
        ReaderBookmarksView.as_view(),
        name="reader-bookmarks",
    ),
    path(
        "reading/sessions/<uuid:identifier>/bookmarks/<uuid:annotation_id>/",
        ReaderBookmarkDetailView.as_view(),
        name="reader-bookmark-detail",
    ),
    path(
        "reading/sessions/<uuid:identifier>/highlights/",
        ReaderHighlightsView.as_view(),
        name="reader-highlights",
    ),
    path(
        "reading/sessions/<uuid:identifier>/highlights/<uuid:annotation_id>/",
        ReaderHighlightDetailView.as_view(),
        name="reader-highlight-detail",
    ),
    path(
        "reading/sessions/<uuid:identifier>/resources/<path:asset_path>",
        ReaderResourceView.as_view(),
        name="reader-resource",
    ),
]
