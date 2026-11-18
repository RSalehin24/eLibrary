from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.models import Bookmark
from apps.access.serializers import BookmarkSerializer, ReadingSessionSerializer
from apps.catalog.models import Book

from .shared import (
    apply_no_store_headers,
    bookmark_queryset_for_book,
    ensure_book_reader_access,
    get_authenticated_token_preview_session,
    reading_session_for_book,
)


class ReaderSessionTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        session = get_authenticated_token_preview_session(request, token)
        if session.user_id is None:
            raise PermissionDenied("Reader progress is unavailable for guest sessions.")
        reading_session, _ = reading_session_for_book(session.user, session.book, preview_session=session)
        return apply_no_store_headers(Response(ReadingSessionSerializer(reading_session).data))

    def post(self, request, token):
        session = get_authenticated_token_preview_session(request, token)
        if session.user_id is None:
            raise PermissionDenied("Reader progress is unavailable for guest sessions.")
        reading_session, _ = reading_session_for_book(session.user, session.book, preview_session=session)
        serializer = ReadingSessionSerializer(reading_session, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=session.user, book=session.book, preview_session=session)
        return apply_no_store_headers(Response(serializer.data))


class ReaderBookmarkTokenListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        session = get_authenticated_token_preview_session(request, token)
        if session.user_id is None:
            raise PermissionDenied("Bookmarks are unavailable for guest sessions.")
        queryset = bookmark_queryset_for_book(session.user, session.book)
        return apply_no_store_headers(Response(BookmarkSerializer(queryset, many=True).data))

    def post(self, request, token):
        session = get_authenticated_token_preview_session(request, token)
        if session.user_id is None:
            raise PermissionDenied("Bookmarks are unavailable for guest sessions.")
        serializer = BookmarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=session.user, book=session.book)
        return apply_no_store_headers(Response(serializer.data, status=status.HTTP_201_CREATED))


class ReaderBookmarkTokenDeleteView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, token, pk):
        session = get_authenticated_token_preview_session(request, token)
        if session.user_id is None:
            raise PermissionDenied("Bookmarks are unavailable for guest sessions.")
        bookmark = bookmark_queryset_for_book(session.user, session.book).filter(pk=pk).first()
        if bookmark is None:
            raise Http404("Bookmark not found.")
        bookmark.delete()
        return apply_no_store_headers(Response(status=status.HTTP_204_NO_CONTENT))


class ReadingSessionView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        book = get_object_or_404(Book, slug=slug)
        ensure_book_reader_access(request, book)
        session, _ = reading_session_for_book(request.user, book)
        return Response(ReadingSessionSerializer(session).data)

    def post(self, request, slug):
        book = get_object_or_404(Book, slug=slug)
        ensure_book_reader_access(request, book)
        session, _ = reading_session_for_book(request.user, book)
        serializer = ReadingSessionSerializer(session, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, book=book)
        return Response(serializer.data)


class BookmarkListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        book = get_object_or_404(Book, slug=slug)
        ensure_book_reader_access(request, book)
        queryset = bookmark_queryset_for_book(request.user, book)
        return apply_no_store_headers(Response(BookmarkSerializer(queryset, many=True).data))

    def post(self, request, slug):
        book = get_object_or_404(Book, slug=slug)
        ensure_book_reader_access(request, book)
        serializer = BookmarkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, book=book)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BookmarkDeleteView(generics.DestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BookmarkSerializer

    def get_queryset(self):
        return Bookmark.objects.filter(user=self.request.user)


__all__ = [
    "BookmarkDeleteView",
    "BookmarkListCreateView",
    "ReaderBookmarkTokenDeleteView",
    "ReaderBookmarkTokenListCreateView",
    "ReaderSessionTokenView",
    "ReadingSessionView",
]
