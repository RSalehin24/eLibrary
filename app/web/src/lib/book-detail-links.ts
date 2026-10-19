import { catalogEntityPath } from "./catalog-entity-path";

type EntityKind = "contributors" | "categories" | "series" | "collections";

export function bookDetailEntityPath({ kind, slug, role = "", personal = false }: { kind: EntityKind; slug: string; role?: string; personal?: boolean }) {
  if (personal) {
    const filter = { contributors: "contributor", categories: "category", series: "series", collections: "collection" }[kind];
    const parameters = new URLSearchParams({ [filter]: slug });
    if (role) parameters.set("contributor_role", role);
    return `/my-books/?${parameters}`;
  }
  return `${catalogEntityPath(kind, slug)}${role ? `?role=${encodeURIComponent(role)}` : ""}`;
}
