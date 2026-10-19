import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { BookDetailPreview, ReaderAccess, ReaderProgress, ReaderSession } from "./types";

export function bookDetailPreview(slug: string, signal: AbortSignal) {
  return apiRequest<BookDetailPreview>(`reading/books/${encodeURIComponent(slug)}/details/`, { signal });
}

export function readerAccess(slug: string, signal: AbortSignal) {
  return apiRequest<ReaderAccess>(`reading/books/${encodeURIComponent(slug)}/access/`, { signal });
}

export function launchReader(slug: string) {
  return apiMutation<ReaderSession>(`reading/books/${encodeURIComponent(slug)}/launch/`, { method: "POST" });
}

export function readerSession(identifier: string, signal: AbortSignal) {
  return apiRequest<ReaderSession>(`reading/sessions/${encodeURIComponent(identifier)}/`, { signal });
}

export function saveReadingProgress(identifier: string, progress: ReaderProgress) {
  return apiMutation<ReaderProgress>(`reading/sessions/${identifier}/progress/`, { method: "PUT", body: JSON.stringify(progress), keepalive: true });
}
