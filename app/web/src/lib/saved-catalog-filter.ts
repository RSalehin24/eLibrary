import { currentBrowseFilters } from "./browse-filters";
import { catalogFilterKeys, catalogSortLabels, type CatalogFilters } from "./catalog-filters";
import { contributorRoles } from "./contributor-roles";

export function savedCatalogFilter(submitted: Record<string, unknown>): CatalogFilters | null {
  const parameters = currentBrowseFilters(submitted);
  const allowed = new Set<string>([...catalogFilterKeys, "q", "author"]);
  if (Object.entries(parameters).some(([key, value]) => !allowed.has(key) || typeof value !== "string" || value.length > 255)) return null;
  const values = Object.fromEntries(Object.entries(parameters).map(([key, value]) => [key, String(value)]));
  if (values.author) { if (values.contributor && values.contributor !== values.author) return null; values.contributor = values.author; values.contributor_role ||= "author"; }
  delete values.author;
  if ((values.q?.length ?? 0) > 120 || !Object.hasOwn(catalogSortLabels, values.sort ?? "")) return null;
  if (values.contributor_role && !Object.hasOwn(contributorRoles, values.contributor_role)) return null;
  if (!["", "mine"].includes(values.ownership ?? "")) return null;
  return values;
}
