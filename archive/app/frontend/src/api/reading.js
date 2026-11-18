import { apiFetch } from "./http";

const BASE = "/access";

export function fetchMyNotes({ book, kind, color, query } = {}) {
  const params = new URLSearchParams();
  if (book) params.set("book", book);
  if (kind) params.set("kind", kind);
  if (color) params.set("color", color);
  if (query) params.set("q", query);
  const qs = params.toString();
  return apiFetch(`${BASE}/me/notes/${qs ? `?${qs}` : ""}`);
}

export function fetchMyReadingProgress() {
  return apiFetch(`${BASE}/me/reading-progress/`);
}

export function fetchBookBookmarks(slug) {
  return apiFetch(`${BASE}/books/${encodeURIComponent(slug)}/bookmarks/`);
}

export function createBookBookmark(slug, body) {
  return apiFetch(`${BASE}/books/${encodeURIComponent(slug)}/bookmarks/`, {
    method: "POST",
    body,
  });
}

export function deleteBookmark(id) {
  return apiFetch(`${BASE}/bookmarks/${id}/`, { method: "DELETE" });
}

export function fetchBookHighlights(slug) {
  return apiFetch(`${BASE}/books/${encodeURIComponent(slug)}/highlights/`);
}

export function createBookHighlight(slug, body) {
  return apiFetch(`${BASE}/books/${encodeURIComponent(slug)}/highlights/`, {
    method: "POST",
    body,
  });
}

export function updateHighlight(id, body) {
  return apiFetch(`${BASE}/highlights/${id}/`, { method: "PATCH", body });
}

export function deleteHighlight(id) {
  return apiFetch(`${BASE}/highlights/${id}/`, { method: "DELETE" });
}
