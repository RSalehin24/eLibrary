from django.http import Http404
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.access.models import Bookmark, Highlight
from apps.access.serializers import (
    BookmarkSerializer,
    HighlightSerializer,
    ReadingSessionSerializer,
)
from apps.catalog.models import Book

from .shared import (
    apply_no_store_headers,
    ensure_book_reader_access,
    get_authenticated_token_preview_session,
)


def _highlight_queryset_for_book(user, book):
    return Highlight.objects.filter(user=user, book=book)


# ---------------------------------------------------------------------------
# Token-based (in-reader) highlight endpoints
# ---------------------------------------------------------------------------


class ReaderHighlightTokenListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, token):
        session = get_authenticated_token_preview_session(request, token)
        if session.user_id is None:
            raise PermissionDenied("Highlights are unavailable for guest sessions.")
        queryset = _highlight_queryset_for_book(session.user, session.book)
        return apply_no_store_headers(
            Response(HighlightSerializer(queryset, many=True).data)
        )

    def post(self, request, token):
        session = get_authenticated_token_preview_session(request, token)
        if session.user_id is None:
            raise PermissionDenied("Highlights are unavailable for guest sessions.")
        serializer = HighlightSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=session.user, book=session.book)
        return apply_no_store_headers(
            Response(serializer.data, status=status.HTTP_201_CREATED)
        )


class ReaderHighlightTokenDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, request, token, pk):
        session = get_authenticated_token_preview_session(request, token)
        if session.user_id is None:
            raise PermissionDenied("Highlights are unavailable for guest sessions.")
        highlight = (
            _highlight_queryset_for_book(session.user, session.book)
            .filter(pk=pk)
            .first()
        )
        if highlight is None:
            raise Http404("Highlight not found.")
        return highlight

    def patch(self, request, token, pk):
        highlight = self._get_object(request, token, pk)
        serializer = HighlightSerializer(highlight, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return apply_no_store_headers(Response(serializer.data))

    def delete(self, request, token, pk):
        highlight = self._get_object(request, token, pk)
        highlight.delete()
        return apply_no_store_headers(Response(status=status.HTTP_204_NO_CONTENT))


# ---------------------------------------------------------------------------
# Slug-based (book-detail page) highlight endpoints
# ---------------------------------------------------------------------------


class HighlightListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, slug):
        book = get_object_or_404(Book, slug=slug)
        ensure_book_reader_access(request, book)
        queryset = _highlight_queryset_for_book(request.user, book)
        return Response(HighlightSerializer(queryset, many=True).data)

    def post(self, request, slug):
        book = get_object_or_404(Book, slug=slug)
        ensure_book_reader_access(request, book)
        serializer = HighlightSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(user=request.user, book=book)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class HighlightDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_object(self, request, pk):
        highlight = Highlight.objects.filter(user=request.user, pk=pk).first()
        if highlight is None:
            raise Http404("Highlight not found.")
        return highlight

    def patch(self, request, pk):
        highlight = self._get_object(request, pk)
        serializer = HighlightSerializer(highlight, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        highlight = self._get_object(request, pk)
        highlight.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Aggregate "My Notes" — across all books, per user
# ---------------------------------------------------------------------------


def _maybe_filter_by_book(queryset, request):
    book_slug = request.query_params.get("book")
    if book_slug:
        queryset = queryset.filter(book__slug=book_slug)
    return queryset


class MyNotesView(APIView):
    """Return bookmarks + highlights + notes + quotes for the current user.

    Query params:
      - book: slug, restrict to a single book
      - kind: 'bookmarks' | 'highlights' | 'notes' | 'quotes' (omit for all)
      - color: highlight/note color filter
      - q: substring search over text/note/label

    'highlights' = kind=highlight with no comment (note="")
    'notes'      = kind=highlight with a comment (note != "")
    'quotes'     = kind=quote
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        kind = request.query_params.get("kind", "").lower()
        color = request.query_params.get("color", "").strip()
        query = request.query_params.get("q", "").strip()

        payload = {}

        if kind in ("", "bookmarks"):
            bookmarks = _maybe_filter_by_book(
                Bookmark.objects.select_related("book").filter(user=request.user),
                request,
            )
            if query:
                bookmarks = bookmarks.filter(
                    note__icontains=query
                ) | bookmarks.filter(label__icontains=query) | bookmarks.filter(
                    preview_text__icontains=query
                )
                bookmarks = bookmarks.distinct()
            payload["bookmarks"] = BookmarkSerializer(bookmarks, many=True).data

        if kind in ("", "highlights"):
            # Pure highlights — no comment attached.
            highlights = _maybe_filter_by_book(
                Highlight.objects.select_related("book")
                .filter(user=request.user, kind="highlight", note=""),
                request,
            )
            if color:
                highlights = highlights.filter(color=color)
            if query:
                highlights = highlights.filter(text__icontains=query).distinct()
            payload["highlights"] = HighlightSerializer(highlights, many=True).data

        if kind in ("", "notes"):
            # Highlights that have a comment/note attached.
            notes_qs = _maybe_filter_by_book(
                Highlight.objects.select_related("book")
                .filter(user=request.user, kind="highlight")
                .exclude(note=""),
                request,
            )
            if color:
                notes_qs = notes_qs.filter(color=color)
            if query:
                notes_qs = (
                    notes_qs.filter(text__icontains=query)
                    | notes_qs.filter(note__icontains=query)
                )
                notes_qs = notes_qs.distinct()
            payload["notes"] = HighlightSerializer(notes_qs, many=True).data

        if kind in ("", "quotes"):
            quotes = _maybe_filter_by_book(
                Highlight.objects.select_related("book")
                .filter(user=request.user, kind="quote"),
                request,
            )
            if query:
                quotes = (
                    quotes.filter(text__icontains=query)
                    | quotes.filter(note__icontains=query)
                )
                quotes = quotes.distinct()
            payload["quotes"] = HighlightSerializer(quotes, many=True).data

        return Response(payload)


class MyReadingProgressView(APIView):
    """List current user's reading progress entries — for 'Continue reading'."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from apps.access.models import ReadingSession

        sessions = (
            ReadingSession.objects.select_related("book")
            .filter(user=request.user)
            .order_by("-last_opened_at")
        )
        return Response(ReadingSessionSerializer(sessions, many=True).data)


__all__ = [
    "HighlightDetailView",
    "HighlightListCreateView",
    "MyNotesView",
    "MyReadingProgressView",
    "ReaderHighlightTokenDetailView",
    "ReaderHighlightTokenListCreateView",
]
