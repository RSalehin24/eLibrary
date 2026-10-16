from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.discovery.entities import public_entities
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.serializers.entities import PublicEntityDetailSerializer
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


class PublicEntityDetailView(VersionedAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="catalog_entity_detail",
        parameters=[
            OpenApiParameter(
                "kind",
                str,
                OpenApiParameter.PATH,
                enum=["contributors", "categories", "series", "collections"],
            )
        ],
        responses={200: PublicEntityDetailSerializer, 404: APIErrorSerializer},
    )
    def get(self, request, **kwargs):
        entity = catalog_object_by_slug(public_entities(kwargs["kind"]), kwargs["slug"])
        return Response(PublicEntityDetailSerializer(entity).data)
