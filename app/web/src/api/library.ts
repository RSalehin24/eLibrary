import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { BookListControls, PhysicalReadingLog, PhysicalReadingLogUpdate } from "./types";

export const readBookListControls = (slugs: readonly string[], signal: AbortSignal) => apiRequest<BookListControls>(`me/book-controls/?${new URLSearchParams(slugs.map(slug => ["slugs", slug]))}`, { signal });

export const readSavedBook = (slug: string, signal: AbortSignal) => apiRequest<{ saved: boolean }>(`me/books/${encodeURIComponent(slug)}/saved/`, { signal });
export const saveBook = (slug: string, saved: boolean) => apiMutation<{ saved: boolean }>(`me/books/${encodeURIComponent(slug)}/saved/`, { method: "PUT", body: JSON.stringify({ saved }) });
export const updatePhysicalLog = (slug: string, fields: PhysicalReadingLogUpdate) => apiMutation<PhysicalReadingLog>(`me/books/${encodeURIComponent(slug)}/physical-log/`, { method: "PUT", body: JSON.stringify(fields) });
