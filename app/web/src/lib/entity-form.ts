import type { EntityKind } from "./catalog-entity";
import { readEditorialFields } from "./editorial-fields";

export function readEntityFields(form: HTMLFormElement, kind: EntityKind) {
  const fields = new FormData(form);
  return { ...readEditorialFields(fields), name: String(fields.get("name") ?? ""),
    ...(kind === "collections" ? { book_ids: fields.getAll("book_ids").map(String) } : {}) };
}
