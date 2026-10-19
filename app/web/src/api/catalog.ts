import { apiRequest } from "./http";
import type { BookCollection, ManagedBooks, WorkspaceSession } from "./types";

export function searchBooks(filters: { query: string; page: number; filters?: Readonly<Record<string, string>> }, signal: AbortSignal) {
  const parameters = new URLSearchParams({ ...filters.filters, q: filters.query, page: String(filters.page) });
  return apiRequest<BookCollection>(`catalog/books/?${parameters}`, { signal });
}

export function readSession(signal: AbortSignal) {
  return apiRequest<WorkspaceSession>("auth/session/", { signal });
}

export function readManagedBooks(page: number, signal: AbortSignal) {
  return apiRequest<ManagedBooks>(`manage/books/?page=${page}`, { signal });
}
