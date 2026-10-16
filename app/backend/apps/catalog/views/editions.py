from django.db.models import IntegerField, Value
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.catalog.discovery.cursors import discovery_page
from apps.catalog.discovery.queries import published_books, with_public_relations
from apps.catalog.discovery.slugs import catalog_object_by_slug
from apps.catalog.serializers.public import (
    PublicBookCollectionSerializer,
    PublicBookListSerializer,
    ReaderPageParametersSerializer,
)
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer


class PublicBookEditionsView(VersionedAPIView):
    authentication_classes = ()
    permission_classes = (AllowAny,)

    @extend_schema(
        operation_id="public_book_editions",
        parameters=[ReaderPageParametersSerializer],
        responses={
            200: PublicBookCollectionSerializer,
            400: APIErrorSerializer,
            404: APIErrorSerializer,
        },
    )
    def get(self, request, slug):
        book = catalog_object_by_slug(
            published_books().only("id", "slug", "group_id"), slug
        )
        serializer = ReaderPageParametersSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        parameters = {
            **serializer.validated_data,
            "q": "",
            "scope": f"editions:{book.pk}",
        }
        books = (
            published_books().filter(group_id=book.group_id).exclude(pk=book.pk)
            if book.group_id
            else published_books().none()
        )
        books = with_public_relations(
            books.annotate(search_rank=Value(0, output_field=IntegerField()))
        )
        entries, cursor = discovery_page(books, parameters)
        return Response(
            {
                "entries": PublicBookListSerializer(entries, many=True).data,
                "next_cursor": cursor,
                "has_more": cursor is not None,
            }
        )
