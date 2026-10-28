import type { CatalogReference } from "@/api/types";

export function catalogReferenceLabel(reference: CatalogReference): string {
  return reference.catalog_code ? `${reference.name} · ${reference.catalog_code}` : reference.name;
}
