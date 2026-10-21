from django.db.models import Count, IntegerField, Subquery, Value
from rest_framework import serializers


class CollectionPaginationSerializer(serializers.Serializer):
    page = serializers.IntegerField(allow_null=True)
    limit = serializers.IntegerField()
    total_count = serializers.IntegerField()
    page_count = serializers.IntegerField()


def counted_collection(queryset):
    matching = queryset.order_by().values("pk")
    totals = (
        queryset.model._default_manager.using(queryset.db)
        .filter(pk__in=matching)
        .order_by()
        .values(collection_count_group=Value(1))
        .annotate(total=Count("pk"))
        .values("total")
    )
    return queryset.annotate(
        collection_total=Subquery(totals, output_field=IntegerField())
    )


def collection_pagination(queryset, parameters, entries):
    count = entries[0].collection_total if entries else queryset.count()
    limit = parameters["limit"]
    return {
        "page": None if parameters.get("cursor") else parameters.get("page", 1),
        "limit": limit,
        "total_count": count,
        "page_count": max(1, (count + limit - 1) // limit),
    }
