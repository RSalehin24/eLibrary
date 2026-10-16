import { apiRequest } from "./http";
import { apiMutation, deleteMutation } from "./mutation";
import type { Bookmark, BookmarkCollection, BookmarkInput, Highlight, HighlightCollection, HighlightInput, PersonalBookmarks, PersonalHighlights } from "./types";

export type AnnotationKind = "bookmarks" | "highlights";

export function readerBookmarks(identifier: string, parameters: { cursor?: string; signal: AbortSignal }) {
  return apiRequest<BookmarkCollection>(`reading/sessions/${identifier}/bookmarks/?${new URLSearchParams({ cursor: parameters.cursor ?? "" })}`, { signal: parameters.signal });
}

export function readerHighlights(identifier: string, parameters: { cursor?: string; signal: AbortSignal }) {
  return apiRequest<HighlightCollection>(`reading/sessions/${identifier}/highlights/?${new URLSearchParams({ cursor: parameters.cursor ?? "" })}`, { signal: parameters.signal });
}

export function saveBookmark(identifier: string, values: BookmarkInput) {
  return apiMutation<Bookmark>(`reading/sessions/${identifier}/bookmarks/`, { method: "PUT", body: JSON.stringify(values) });
}

export function createHighlight(identifier: string, values: HighlightInput) {
  return apiMutation<Highlight>(`reading/sessions/${identifier}/highlights/`, { method: "POST", body: JSON.stringify(values) });
}

export function personalAnnotations(kind: AnnotationKind, parameters: { cursor?: string; signal: AbortSignal }) {
  return apiRequest<PersonalBookmarks | PersonalHighlights>(`me/${kind}/?${new URLSearchParams({ cursor: parameters.cursor ?? "" })}`, { signal: parameters.signal });
}

export function personalAnnotation(kind: AnnotationKind, identifier: string, signal: AbortSignal) {
  return apiRequest<Bookmark | Highlight>(`me/${kind}/${identifier}/`, { signal });
}

export function updateNote(kind: AnnotationKind, values: { id: string; note: string; expected_updated_at: string }) {
  return apiMutation<Bookmark | Highlight>(`me/${kind}/${values.id}/`, { method: "PATCH", body: JSON.stringify(values) });
}

export function deleteAnnotation(kind: AnnotationKind, identifier: string) {
  return deleteMutation(`me/${kind}/${identifier}/`);
}
