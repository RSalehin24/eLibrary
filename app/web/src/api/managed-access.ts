import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { AccessReferenceKind, AccessReferences, ManagedAccount, ManagedAccountUpdate, ManagedGrant, ManagedGrantCreate, ManagedGrants, ManagedGrantUpdate } from "./types";

export const readManagedAccount = (id: number, signal?: AbortSignal) => apiRequest<ManagedAccount>(`manage/users/${id}/`, { signal });
export const updateManagedAccount = (id: number, values: ManagedAccountUpdate) => apiMutation<ManagedAccount>(`manage/users/${id}/`, { method: "PATCH", body: JSON.stringify(values) });
export const readManagedGrants = (id: number, query: string, signal?: AbortSignal) => apiRequest<ManagedGrants>(`manage/users/${id}/grants/?${query}`, { signal });
export const createManagedGrant = (id: number, values: ManagedGrantCreate) => apiMutation<ManagedGrant>(`manage/users/${id}/grants/`, { method: "POST", body: JSON.stringify(values) });
export const updateManagedGrant = (accountId: number, grantId: string, values: ManagedGrantUpdate) => apiMutation<ManagedGrant>(`manage/users/${accountId}/grants/${grantId}/`, { method: "PATCH", body: JSON.stringify(values) });
export const readAccessReferences = (kind: AccessReferenceKind, query: string, signal?: AbortSignal) => apiRequest<AccessReferences>(`manage/access/references/?${new URLSearchParams({ kind, q: query, limit: "24" })}`, { signal });
