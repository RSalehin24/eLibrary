import { catalogEntityPath } from "./catalog-entity-path";

type EntityKind = "contributors" | "categories" | "series" | "collections";

export function isPersonalLibraryView(value: string | null): value is string {
  return value !== null && ["all", "owned", "saved", "recent", "granted"].includes(value);
}

export function bookDetailEntityPath({ kind, slug, role = "", personal = false, view }: { kind: EntityKind; slug: string; role?: string; personal?: boolean; view?: string }) {
  if (personal) {
    const filter = { contributors: "contributor", categories: "category", series: "series", collections: "collection" }[kind];
    const parameters = new URLSearchParams({ [filter]: slug });
    if (role) parameters.set("contributor_role", role);
    if (view && isPersonalLibraryView(view) && view !== "all") parameters.set("view", view);
    return `/my-books/?${parameters}`;
  }
  return `${catalogEntityPath(kind, slug)}${role ? `?role=${encodeURIComponent(role)}` : ""}`;
}
