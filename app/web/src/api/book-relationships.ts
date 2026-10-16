import { apiMutation } from "./mutation";
import type { BookRelationships, BookRelationshipsUpdate } from "./types";

export function updateBookRelationships(slug: string, fields: BookRelationshipsUpdate) {
  return apiMutation<BookRelationships>(`manage/books/${encodeURIComponent(slug)}/relationships/`, { method: "PATCH", body: JSON.stringify(fields) });
}
