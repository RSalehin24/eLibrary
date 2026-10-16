import { apiRequest } from "./http";
import type { BookCollection, ManagedBooks, WorkspaceSession } from "./types";

export function searchBooks(filters: { query: string; page: number }, signal: AbortSignal) {
  const parameters = new URLSearchParams({ q: filters.query, page: String(filters.page) });
  return apiRequest<BookCollection>(`catalog/books/?${parameters}`, { signal });
}

export function readSession(signal: AbortSignal) {
  return apiRequest<WorkspaceSession>("auth/session/", { signal });
}

export function readManagedBooks(page: number, signal: AbortSignal) {
  return apiRequest<ManagedBooks>(`manage/books/?page=${page}`, { signal });
}
