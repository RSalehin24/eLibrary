from apps.access.views.annotation_launch import (
    AnnotationReaderLaunchView,
    HighlightReaderLaunchView,
)
from apps.accounts.management_access.bulk import ManagedAccountBulkGrantView
from apps.accounts.profile_image_api import AccountProfileImageView
from apps.catalog.views.editions import PublicBookEditionsView
from apps.catalog.views.personal import PhysicalReadingLogView, SavedBookView
from apps.common.saved_filter_api import SavedFilterDeleteView, SavedFiltersView
from django.urls import path

personal_library_routes = [
    path(
        "me/bookmarks/<uuid:annotation_id>/launch/",
        AnnotationReaderLaunchView.as_view(),
        name="personal-bookmark-launch",
    ),
    path(
        "me/highlights/<uuid:annotation_id>/launch/",
        HighlightReaderLaunchView.as_view(),
        name="personal-highlight-launch",
    ),
    path(
        "manage/users/<int:identifier>/grants/bulk/",
        ManagedAccountBulkGrantView.as_view(),
        name="managed-account-bulk-grants",
    ),
    path("me/saved-filters/", SavedFiltersView.as_view(), name="saved-filters"),
    path(
        "me/saved-filters/<uuid:identifier>/",
        SavedFilterDeleteView.as_view(),
        name="saved-filter-delete",
    ),
    path(
        "auth/profile/image/",
        AccountProfileImageView.as_view(),
        name="account-profile-image",
    ),
    path("me/books/<str:slug>/saved/", SavedBookView.as_view(), name="saved-book"),
    path(
        "me/books/<str:slug>/physical-log/",
        PhysicalReadingLogView.as_view(),
        name="physical-reading-log",
    ),
    path(
        "catalog/books/<str:slug>/editions/",
        PublicBookEditionsView.as_view(),
        name="public-book-editions",
    ),
]
