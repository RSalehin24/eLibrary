import { apiRequest } from "./http";
import type { SourceEntries, SourceEntry } from "./types";

export const readSources = (query: string, signal?: AbortSignal) => apiRequest<SourceEntries>(`manage/sources/?${query}`, { signal });
export const readSource = (id: string, signal?: AbortSignal) => apiRequest<SourceEntry>(`manage/sources/${id}/`, { signal });
