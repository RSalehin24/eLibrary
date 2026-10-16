from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.pagination import BoundedAdminPagination
from apps.common.permissions import CanManageAccess

from .queries import (
    access_references,
    account_grants,
    managed_account,
    managed_accounts,
)
from .serializers import (
    AccessListParametersSerializer,
    AccessReferenceCollectionSerializer,
    AccessReferenceParametersSerializer,
    AccessReferenceSerializer,
    ManagedAccountCollectionSerializer,
    ManagedAccountParametersSerializer,
    ManagedAccountSerializer,
    ManagedAccountUpdateSerializer,
    ManagedGrantCollectionSerializer,
    ManagedGrantCreateSerializer,
    ManagedGrantSerializer,
    ManagedGrantUpdateSerializer,
)
from .services import create_managed_grant, update_managed_account, update_managed_grant


def validated_parameters(serializer_class, request):
    parameters = serializer_class(data=request.query_params)
    parameters.is_valid(raise_exception=True)
    return parameters.validated_data


def paginated_response(queryset, serializer, request):
    pagination = BoundedAdminPagination()
    entries: list | None = pagination.paginate_queryset(queryset, request)
    return pagination.get_paginated_response(
        serializer(entries, many=True, context={"actor": request.user}).data
    )


class ManagedAccountListView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="managed_accounts_list",
        parameters=[ManagedAccountParametersSerializer],
        responses={
            200: ManagedAccountCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        parameters = validated_parameters(ManagedAccountParametersSerializer, request)
        return paginated_response(
            managed_accounts(parameters), ManagedAccountSerializer, request
        )


class ManagedAccountDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="managed_account_read",
        responses={
            200: ManagedAccountSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        return Response(
            ManagedAccountSerializer(
                managed_account(identifier), context={"actor": request.user}
            ).data
        )

    @extend_schema(
        operation_id="managed_account_update",
        request=ManagedAccountUpdateSerializer,
        responses={
            200: ManagedAccountSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def patch(self, request, identifier):
        account = update_managed_account(request.user, identifier, request.data)
        return Response(
            ManagedAccountSerializer(account, context={"actor": request.user}).data
        )


class ManagedAccountGrantListView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="managed_account_grants_list",
        parameters=[AccessListParametersSerializer],
        responses={
            200: ManagedGrantCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, identifier):
        validated_parameters(AccessListParametersSerializer, request)
        return paginated_response(
            account_grants(managed_account(identifier)), ManagedGrantSerializer, request
        )

    @extend_schema(
        operation_id="managed_account_grant_create",
        request=ManagedGrantCreateSerializer,
        responses={
            201: ManagedGrantSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def post(self, request, identifier):
        grant = create_managed_grant(request.user, identifier, request.data)
        return Response(ManagedGrantSerializer(grant).data, status=201)


class ManagedAccountGrantDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="managed_account_grant_update",
        request=ManagedGrantUpdateSerializer,
        responses={
            200: ManagedGrantSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def patch(self, request, identifier, grant_id):
        grant = update_managed_grant(request.user, (identifier, grant_id), request.data)
        return Response(ManagedGrantSerializer(grant).data)


class AccessReferencesView(VersionedAPIView):
    permission_classes = (IsAuthenticated, CanManageAccess)

    @extend_schema(
        operation_id="access_references_list",
        parameters=[AccessReferenceParametersSerializer],
        responses={
            200: AccessReferenceCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        parameters = validated_parameters(AccessReferenceParametersSerializer, request)
        return paginated_response(
            access_references(parameters), AccessReferenceSerializer, request
        )
