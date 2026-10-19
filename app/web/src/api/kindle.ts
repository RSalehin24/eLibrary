import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { KindleCollection, KindleOperation, KindleOptions, KindleRequest, OperationAccepted } from "./types";

export const kindleOptions = (slug: string, signal?: AbortSignal) => apiRequest<KindleOptions>(`delivery/books/${encodeURIComponent(slug)}/kindle/`, { signal });
export const kindleOperation = (identifier: string, signal?: AbortSignal) => apiRequest<KindleOperation>(`delivery/operations/${identifier}/`, { signal });
export const kindleHistory = (cursor: string, signal?: AbortSignal, filters = "") => apiRequest<KindleCollection>(`me/kindle/?${new URLSearchParams({ ...Object.fromEntries(new URLSearchParams(filters)), cursor })}`, { signal });
export const requestKindle = (slug: string, values: KindleRequest) => apiMutation<OperationAccepted>(`delivery/books/${encodeURIComponent(slug)}/kindle/`, { method: "POST", body: JSON.stringify(values) });
export const cancelKindle = (operation: KindleOperation) => apiMutation<OperationAccepted>(`delivery/operations/${operation.id}/`, { method: "POST", body: JSON.stringify({ expected_updated_at: operation.updated_at }) });
