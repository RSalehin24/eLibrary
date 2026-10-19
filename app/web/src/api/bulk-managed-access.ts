import { apiMutation } from "./mutation";
import type { ManagedGrantBulkResult, ManagedGrantCreate } from "./types";

export const createManagedGrants = (id: number, entries: ManagedGrantCreate[]) => apiMutation<ManagedGrantBulkResult>(`manage/users/${id}/grants/bulk/`, { method: "POST", body: JSON.stringify({ entries }) });
