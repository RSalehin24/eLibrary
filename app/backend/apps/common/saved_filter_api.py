from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.common.api import VersionedAPIView
from apps.common.api_serializers import AdminPaginationSerializer, APIErrorSerializer
from apps.common.models import SavedFilter, SavedFilterTarget
from apps.common.pagination import BoundedAdminPagination
from apps.common.saved_filter_services import create_saved_filter
from apps.common.validation import reject_unknown_fields


class SavedFilterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SavedFilter
        fields = ("id", "target", "name", "params", "created_at", "updated_at")
        read_only_fields = fields


class SavedFilterParametersSerializer(serializers.Serializer):
    target = serializers.ChoiceField(
        choices=SavedFilterTarget.choices, default="catalog"
    )
    page = serializers.IntegerField(min_value=1, default=1)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)


class SavedFilterCollectionSerializer(serializers.Serializer):
    entries = SavedFilterSerializer(many=True)
    pagination = AdminPaginationSerializer()


class SavedFilterCreateSerializer(serializers.Serializer):
    operation_id = serializers.UUIDField()
    target = serializers.ChoiceField(choices=SavedFilterTarget.choices)
    name = serializers.CharField(max_length=120)
    params = serializers.DictField(
        child=serializers.CharField(max_length=255, allow_blank=True), default=dict
    )

    def validate(self, values):
        reject_unknown_fields(self)
        return values


class SavedFiltersView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="saved_filters_list",
        parameters=[SavedFilterParametersSerializer],
        responses={200: SavedFilterCollectionSerializer, 400: APIErrorSerializer},
    )
    def get(self, request):
        parameters = SavedFilterParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        queryset = SavedFilter.objects.filter(
            owner=request.user, target=parameters.validated_data["target"]
        ).order_by("name", "id")
        pagination = BoundedAdminPagination()
        entries = pagination.paginate_queryset(queryset, request, view=self)
        return pagination.get_paginated_response(
            SavedFilterSerializer(entries, many=True).data
        )

    @extend_schema(
        operation_id="saved_filter_create",
        request=SavedFilterCreateSerializer,
        responses={
            201: SavedFilterSerializer,
            400: APIErrorSerializer,
            409: APIErrorSerializer,
        },
    )
    def post(self, request):
        serializer = SavedFilterCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            SavedFilterSerializer(
                create_saved_filter(request.user, serializer.validated_data)
            ).data,
            status=201,
        )


class SavedFilterDeleteView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        operation_id="saved_filter_delete",
        responses={204: None, 404: APIErrorSerializer},
    )
    def delete(self, request, identifier):
        saved = get_object_or_404(
            SavedFilter.objects.filter(owner=request.user), pk=identifier
        )
        saved.delete()
        return Response(status=204)
