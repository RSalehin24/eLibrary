from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.catalog.editorial.entity_policy import (
    ENTITY_KINDS,
    filtered_entities,
    require_entity_workspace,
)
from apps.catalog.editorial.entity_service import (
    create_entity,
    entity_command,
    entity_detail,
    update_entity,
)
from apps.catalog.editorial.references import catalog_references
from apps.catalog.serializers.managed_entities import (
    CatalogReferenceCollectionSerializer,
    CatalogReferenceParametersSerializer,
    EntityCommandSerializer,
    EntityCreateSerializer,
    EntityUpdateSerializer,
    ManagedEntityCollectionSerializer,
    ManagedEntityListSerializer,
    ManagedEntityParametersSerializer,
    ManagedEntitySerializer,
)
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer
from apps.common.pagination import BoundedAdminPagination

KIND_PARAMETER = OpenApiParameter("kind", str, OpenApiParameter.PATH, enum=ENTITY_KINDS)
ENTITY_RESPONSES = {
    200: ManagedEntitySerializer,
    400: APIErrorSerializer,
    403: APIErrorSerializer,
    404: APIErrorSerializer,
    409: APIErrorSerializer,
}


def entity_response(actor, target, status=200):
    return Response(
        ManagedEntitySerializer(entity_detail(actor, *target)).data, status=status
    )


class ManagedEntityListView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_entities_list",
        parameters=[KIND_PARAMETER, ManagedEntityParametersSerializer],
        responses={
            200: ManagedEntityCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, kind):
        require_entity_workspace(request.user)
        parameters = ManagedEntityParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        pagination = BoundedAdminPagination()
        entries: list | None = pagination.paginate_queryset(
            filtered_entities(request.user, kind, parameters.validated_data["q"]),
            request,
            view=self,
        )
        return pagination.get_paginated_response(
            ManagedEntityListSerializer(entries, many=True).data
        )

    @extend_schema(
        operation_id="managed_entity_create",
        parameters=[KIND_PARAMETER],
        request=EntityCreateSerializer,
        responses={**ENTITY_RESPONSES, 201: ManagedEntitySerializer},
    )
    def post(self, request, kind):
        parameters = EntityCreateSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        entity = create_entity(request.user, kind, parameters.validated_data)
        return entity_response(request.user, (kind, entity.pk), status=201)


class ManagedEntityDetailView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="managed_entity_detail",
        parameters=[KIND_PARAMETER],
        responses=ENTITY_RESPONSES,
    )
    def get(self, request, kind, identifier):
        return entity_response(request.user, (kind, identifier))

    @extend_schema(
        operation_id="managed_entity_update",
        parameters=[KIND_PARAMETER],
        request=EntityUpdateSerializer,
        responses=ENTITY_RESPONSES,
    )
    def patch(self, request, kind, identifier):
        parameters = EntityUpdateSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        update_entity(request.user, (kind, identifier), parameters.validated_data)
        return entity_response(request.user, (kind, identifier))

    @extend_schema(
        operation_id="managed_entity_command",
        parameters=[KIND_PARAMETER],
        request=EntityCommandSerializer,
        responses=ENTITY_RESPONSES,
    )
    def post(self, request, kind, identifier):
        parameters = EntityCommandSerializer(data=request.data)
        parameters.is_valid(raise_exception=True)
        entity_command(request.user, (kind, identifier), parameters.validated_data)
        return entity_response(request.user, (kind, identifier))


class CatalogReferencesView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="catalog_references_list",
        parameters=[CatalogReferenceParametersSerializer],
        responses={
            200: CatalogReferenceCollectionSerializer,
            400: APIErrorSerializer,
            403: APIErrorSerializer,
        },
    )
    def get(self, request):
        require_entity_workspace(request.user)
        parameters = CatalogReferenceParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        values = parameters.validated_data
        entries = list(catalog_references(request.user, values)[: values["limit"] + 1])
        return Response(
            {
                "entries": entries[: values["limit"]],
                "has_more": len(entries) > values["limit"],
            }
        )
