from typing import ClassVar

from drf_spectacular.utils import extend_schema
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.access.models import Bookmark, Highlight
from apps.access.reader_serializers import ReaderSessionSerializer
from apps.access.reading.annotation_launch import launch_annotation_reader
from apps.common.api import VersionedAPIView
from apps.common.api_serializers import APIErrorSerializer

from .reader_v1 import reader_session_data


class AnnotationReaderLaunchView(VersionedAPIView):
    permission_classes = (IsAuthenticated,)
    model: ClassVar[type[Bookmark] | type[Highlight]] = Bookmark

    @extend_schema(
        request=None,
        responses={200: ReaderSessionSerializer, 403: APIErrorSerializer,
                   404: APIErrorSerializer, 409: APIErrorSerializer},
    )
    def post(self, request, annotation_id):
        session = launch_annotation_reader(request.user, self.model, annotation_id)
        return Response(reader_session_data(session))


class HighlightReaderLaunchView(AnnotationReaderLaunchView):
    model = Highlight
