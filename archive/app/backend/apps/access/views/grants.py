from django.db.models import Count
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.models import (
    ACCOUNT_MANAGEABLE_PERMISSION_SCOPES,
    SCOPED_PERMISSION_SCOPES,
    PermissionGrant,
)
from apps.access.serializers import PermissionGrantSerializer
from apps.catalog.models import Book, Category, Contributor, ContributorRole
from apps.common.permissions import IsSuperAdmin


class PermissionGrantListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = PermissionGrantSerializer
    queryset = PermissionGrant.objects.select_related("user", "book", "category", "contributor").all()

    def perform_create(self, serializer):
        if serializer.validated_data.get("user") == self.request.user:
            raise PermissionDenied("You cannot change your own scoped access rules.")
        serializer.save(granted_by=self.request.user)


class PermissionGrantDetailView(generics.DestroyAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = PermissionGrantSerializer
    queryset = PermissionGrant.objects.select_related("user", "book", "category", "contributor").all()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user_id == request.user.id:
            raise PermissionDenied("You cannot change your own scoped access rules.")
        return super().destroy(request, *args, **kwargs)


class AccessReferenceDataView(APIView):
    permission_classes = [IsSuperAdmin]

    def get(self, request):
        view_mode = str(request.query_params.get("view", "access") or "access").strip().lower()
        account_scopes = [{"value": scope.value, "label": scope.label} for scope in ACCOUNT_MANAGEABLE_PERMISSION_SCOPES]
        if view_mode == "users":
            return Response(
                {
                    "users": [],
                    "books": [],
                    "categories": [],
                    "writers": [],
                    "account_scopes": account_scopes,
                    "scoped_scopes": [],
                }
            )

        # Use annotate to compute grant_count in a single query instead of N+1.
        # capabilities (capability_scopes) are not needed in the grants reference
        # dropdown and would cause an extra DB query per non-superuser.
        users = [
            {
                "id": user.id,
                "email": user.email,
                "name": user.display_name,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "grant_count": user.grant_count_value,
            }
            for user in request.user.__class__.objects.annotate(
                grant_count_value=Count("permission_grants"),
            ).order_by("email")
        ]
        books = [
            {"id": book.id, "title": book.title, "slug": book.slug}
            for book in Book.objects.only("id", "title", "slug").order_by("title")
        ]
        categories = [
            {"id": category.id, "name": category.name, "slug": category.slug}
            for category in Category.objects.only("id", "name", "slug").order_by("name")
        ]
        writers = [
            {"id": contributor.id, "name": contributor.name, "slug": contributor.slug}
            for contributor in Contributor.objects.only("id", "name", "slug")
            .filter(book_contributions__role=ContributorRole.AUTHOR)
            .distinct()
            .order_by("name")
        ]
        scoped_scopes = [{"value": scope.value, "label": scope.label} for scope in SCOPED_PERMISSION_SCOPES]
        return Response(
            {
                "users": users,
                "books": books,
                "categories": categories,
                "writers": writers,
                "account_scopes": account_scopes,
                "scoped_scopes": scoped_scopes,
            }
        )


__all__ = [
    "AccessReferenceDataView",
    "PermissionGrantDetailView",
    "PermissionGrantListCreateView",
]
