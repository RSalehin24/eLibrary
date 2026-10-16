import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { ReaderAccess, ReaderProgress, ReaderSession } from "./types";

export function readerAccess(slug: string, signal: AbortSignal) {
  return apiRequest<ReaderAccess>(`reading/books/${encodeURIComponent(slug)}/access/`, { signal });
}

export function launchReader(slug: string) {
  return apiMutation<ReaderSession>(`reading/books/${encodeURIComponent(slug)}/launch/`, { method: "POST" });
}

export function saveReadingProgress(identifier: string, progress: ReaderProgress) {
  return apiMutation<ReaderProgress>(`reading/sessions/${identifier}/progress/`, { method: "PUT", body: JSON.stringify(progress), keepalive: true });
}
