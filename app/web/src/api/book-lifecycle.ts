import { apiRequest } from "./http";
import { apiMutation, emptyMutation } from "./mutation";
import type { BookControls, ManagedBookDetail, RegenerationAccepted } from "./types";

export const readBookControls = (slug: string, signal: AbortSignal) => apiRequest<BookControls>(`manage/books/${encodeURIComponent(slug)}/controls/`, { signal });
export const regenerateBook = (book: ManagedBookDetail, operation: string) => apiMutation<RegenerationAccepted>(`manage/books/${encodeURIComponent(book.slug)}/regenerate/`, { method: "POST", body: JSON.stringify({ operation_id: operation, expected_updated_at: book.updated_at }) });
export const removeBook = (book: ManagedBookDetail) => emptyMutation(`manage/books/${encodeURIComponent(book.slug)}/`, { method: "DELETE", body: JSON.stringify({ expected_updated_at: book.updated_at }) });
