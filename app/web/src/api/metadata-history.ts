import { apiRequest } from "./http";
import type { MetadataHistory } from "./types";

export function readMetadataHistory(slug: string, page: number, signal?: AbortSignal) {
  return apiRequest<MetadataHistory>(`manage/books/${encodeURIComponent(slug)}/history/?page=${page}&limit=10`, { signal });
}
