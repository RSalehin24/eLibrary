import { savedCatalogFilter } from "./saved-catalog-filter";
import { savedQueueFilter, jobFilterKeys } from "./job-filters";
import { kindleHistoryKeys, kindleHistoryQuery } from "./kindle-history";
import { validDirectoryFilters } from "./entity-directory-filters";

type LegacyQuery = Record<string, string | string[] | undefined>;
const aliases: Readonly<Record<string, string>> = {
  home: "/catalog/", library: "/catalog/", "manual-books": "/physical-books/",
  "created-books": "/my-books/", "kindle-sent": "/kindle/", access: "/manage/users-access/",
  "two-factor-setup": "/profile/", "demo-login": "/login/", processing: "/manage/sources/",
  "processing-catalog-books": "/manage/sources/", "processing-automation": "/manage/automations/",
  create: "/manage/sources/", "processing-my-requests": "/manage/sources/", queue: "/manage/jobs/",
  "on-hold": "/manage/jobs/", "processing-failed-requests": "/manage/jobs/",
  "processing-duplicate-requests": "/manage/jobs/", incomplete: "/manage/unfinished/",
  "processing-incomplete-check": "/manage/unfinished/", reprocessing: "/manage/jobs/",
  "multipage-toc": "/manage/jobs/", "processing-multi-page-toc": "/manage/jobs/",
};
const roles: Readonly<Record<string, string>> = { writers: "author", translators: "translator", editors: "editor", compilers: "editor", publishers: "publisher" };
const catalogKeys = ["q", "contributor", "contributor_role", "author", "series", "category", "collection", "ownership", "record_type", "sort"];

function selectedValues(parameters: LegacyQuery, keys: readonly string[]) {
  return Object.fromEntries(keys.flatMap(key => typeof parameters[key] === "string" && parameters[key] ? [[key, parameters[key] as string]] : []));
}

function pageQuery(parameters: LegacyQuery): Record<string, string> {
  const page = parameters.page;
  return typeof page === "string" && /^[1-9][0-9]{0,3}$/.test(page) ? { page } : {};
}

function catalogValues(parameters: LegacyQuery, physical: boolean) {
  const values = savedCatalogFilter({ record_type: physical ? "manual" : "digital", ...selectedValues(parameters, catalogKeys) });
  if (!values) return null;
  const extra = physical ? selectedValues(parameters, ["writer", "translator", "editor", "publisher", "binding", "language"]) : {};
  if (extra.binding && !["hard_cover", "paper_back"].includes(extra.binding)) return null;
  if (Object.values(extra).some(value => value.length > 255)) return null;
  return { ...values, ...extra };
}

function sourceValues(route: string, parameters: LegacyQuery) {
  const values = selectedValues(parameters, ["q", "status"]);
  if ((values.q?.length ?? 0) > 200 || values.status && !["all", "unlinked", "linked", "removed", "updated"].includes(values.status)) return null;
  if (["create", "processing-my-requests"].includes(route)) values.status = "unlinked";
  return values;
}

function jobValues(route: string, parameters: LegacyQuery) {
  const values = savedQueueFilter(selectedValues(parameters, jobFilterKeys));
  if (!values) return null;
  if (["on-hold", "processing-failed-requests", "processing-duplicate-requests"].includes(route)) values.view = "recovery";
  if (route === "reprocessing") values.kind = "process_source";
  if (["multipage-toc", "processing-multi-page-toc"].includes(route)) {
    values.kind = "process_source";
    values.layout = "multi_page";
  }
  return values;
}

export function legacyRouteTarget(route: string, parameters: LegacyQuery): string | null {
  if (Object.values(parameters).some(value => Array.isArray(value) || typeof value === "string" && /[\\\u0000-\u001f]/.test(value))) return null;
  if (route === "reader") {
    const slug = parameters.slug;
    return typeof slug === "string" && slug.length <= 255 && /^[\p{L}\p{M}\p{N}_-]+$/u.test(slug) ? `/my-books/${encodeURIComponent(slug)}/` : "/my-books/";
  }
  if (Object.hasOwn(roles, route)) {
    if (typeof parameters.q === "string" && parameters.q.length > 120 || typeof parameters.record_type === "string" && !["all", "manual", "digital"].includes(parameters.record_type)) return null;
    const values = selectedValues(parameters, ["q", "record_type", "sort", "created_after", "created_before"]);
    if (!validDirectoryFilters(values)) return null;
    const query = new URLSearchParams({ ...values, ...pageQuery(parameters), role: roles[route] });
    return `/contributors/?${query}`;
  }
  if (!Object.hasOwn(aliases, route)) return null;
  const pathname = aliases[route];
  let values: Record<string, string> | null = {};
  if (["/catalog/", "/physical-books/", "/my-books/"].includes(pathname)) values = catalogValues(parameters, pathname === "/physical-books/");
  if (pathname === "/manage/sources/") values = sourceValues(route, parameters);
  if (pathname === "/manage/jobs/") values = jobValues(route, parameters);
  if (pathname === "/kindle/") {
    const selected = selectedValues(parameters, kindleHistoryKeys);
    if (typeof parameters.author === "string" && !selected.contributor) selected.contributor = parameters.author;
    values = Object.fromEntries(new URLSearchParams(kindleHistoryQuery(selected)));
  }
  if (!values) return null;
  const query = new URLSearchParams({ ...values, ...pageQuery(parameters) });
  return pathname + (query.size ? `?${query}` : "");
}
