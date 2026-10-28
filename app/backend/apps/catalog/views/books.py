from typing import ClassVar

from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.exports import (
    build_book_tickets_pdf_response,
    build_books_csv_response,
    build_books_pdf_response,
)
from apps.catalog.models import Book, UserBook
from apps.catalog.serializers import BookDetailSerializer, BookListSerializer

from .shared import BookQueryMixin, OptionalPaginationListMixin


class BookListView(OptionalPaginationListMixin, BookQueryMixin, generics.ListAPIView):
    permission_classes: ClassVar = [IsAuthenticated]
    serializer_class = BookListSerializer
    pagination_default_limit = 10
    pagination_max_limit = 100


class CsvPassthroughRenderer(BaseRenderer):
    media_type = "text/csv"
    format = "csv"
    charset = "utf-8"
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data if data is not None else b""


class PdfPassthroughRenderer(BaseRenderer):
    media_type = "application/pdf"
    format = "pdf"
    charset = None
    render_style = "binary"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        return data if data is not None else b""


class BookExportView(BookQueryMixin, APIView):
    permission_classes: ClassVar = [IsAuthenticated]
    renderer_classes: ClassVar = [
        JSONRenderer,
        CsvPassthroughRenderer,
        PdfPassthroughRenderer,
    ]

    def get(self, request):
        export_format = request.query_params.get("format", "csv").strip().lower()
        books = list(self.get_queryset())
        if export_format == "csv":
            return build_books_csv_response(books)
        if export_format == "pdf":
            try:
                return build_books_pdf_response(books)
            except RuntimeError as exc:
                return Response(
                    {"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
        return Response(
            {"detail": "format must be csv or pdf."}, status=status.HTTP_400_BAD_REQUEST
        )


class BookTicketExportView(BookQueryMixin, APIView):
    permission_classes: ClassVar = [IsAuthenticated]
    renderer_classes: ClassVar = [JSONRenderer, PdfPassthroughRenderer]

    def get(self, request):
        try:
            return build_book_tickets_pdf_response(list(self.get_queryset()))
        except RuntimeError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )


class BookMyBooksView(APIView):
    permission_classes: ClassVar = [IsAuthenticated]

    def get_book(self):
        return get_object_or_404(
            Book, slug=self.kwargs["slug"], deleted_at__isnull=True
        )

    def post(self, request, *args, **kwargs):
        book = self.get_book()
        ownership, _created = UserBook.objects.get_or_create(
            user=request.user, book=book
        )
        book.is_in_my_books = True
        book.user_owns_book = True
        book.my_books_added_at = ownership.created_at
        return Response(BookDetailSerializer(book, context={"request": request}).data)

    def delete(self, request, *args, **kwargs):
        UserBook.objects.filter(user=request.user, book=self.get_book()).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
