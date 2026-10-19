import { apiRequest } from "./http";
import { apiMutation, deleteMutation } from "./mutation";
import type { SavedFilter, SavedFilterCreate, SavedFilters } from "./types";

export const readSavedFilters = (target: SavedFilter["target"], page: number, signal: AbortSignal) => apiRequest<SavedFilters>(`me/saved-filters/?${new URLSearchParams({ target, page: String(page), limit: "100" })}`, { signal });
export const createSavedFilter = (values: SavedFilterCreate) => apiMutation<SavedFilter>("me/saved-filters/", { method: "POST", body: JSON.stringify(values) });
export const deleteSavedFilter = (identifier: string) => deleteMutation(`me/saved-filters/${identifier}/`);
