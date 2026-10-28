import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { CatalogReferences, EntityCreate, EntityUpdate, ManagedEntity } from "./types";
import type { EntityKind } from "@/lib/catalog-entity";
export type EntityCommand = "publish" | "withdraw";

export function readCatalogReferences(kind: EntityKind | "books", query: string, signal: AbortSignal) {
  const parameters = new URLSearchParams({ kind, q: query, limit: "24" });
  return apiRequest<CatalogReferences>(`manage/catalog-references/?${parameters}`, { signal });
}

export function managedEntityPath(kind: EntityKind, identifier?: string) {
  return `manage/entities/${kind}/${identifier ? `${encodeURIComponent(identifier)}/` : ""}`;
}

export function createManagedEntity(kind: EntityKind, input: EntityCreate) {
  return apiMutation<ManagedEntity>(managedEntityPath(kind), { method: "POST", body: JSON.stringify(input) });
}

export function updateManagedEntity(kind: EntityKind, entity: ManagedEntity, input: Omit<EntityUpdate, "expected_updated_at">) {
  return apiMutation<ManagedEntity>(managedEntityPath(kind, entity.id), { method: "PATCH", body: JSON.stringify({ ...input, expected_updated_at: entity.updated_at }) });
}

export function commandManagedEntity(kind: EntityKind, entity: ManagedEntity, action: EntityCommand) {
  return apiMutation<ManagedEntity>(managedEntityPath(kind, entity.id), { method: "POST", body: JSON.stringify({ action, expected_updated_at: entity.updated_at }) });
}
