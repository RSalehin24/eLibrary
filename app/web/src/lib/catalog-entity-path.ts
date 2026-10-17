import type { EntityKind } from "./catalog-entity";

export function catalogEntityPath(kind: EntityKind, slug: string) {
  return `/${kind}/${encodeURIComponent(slug)}/`;
}
