from apps.accounts.profile_image_api import AccountProfileImageView
from apps.catalog.views.editions import PublicBookEditionsView
from apps.catalog.views.personal import PhysicalReadingLogView, SavedBookView
from django.urls import path

personal_library_routes = [
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
