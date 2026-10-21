import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { APIError } from "@/api/http";
import { publicRequest } from "@/api/server";
import type { EntityCollection } from "@/api/types";
import { catalogEntityPath, entityLabels, type EntityKind } from "@/lib/catalog-entity";
import { contributorRoles } from "@/lib/contributor-roles";
import { catalogPageNumber, queryValue, type RouteQuery } from "@/lib/route-query";
import { directorySortLabels } from "@/lib/entity-directory-filters";
import { retiredFilterRedirect } from "@/lib/browse-filters";
import { CatalogPagination } from "./catalog-pagination";
import { CatalogBrowseNav } from "./catalog-browse-nav";
import { SiteInput, SiteNumber, SiteSelect, SiteText } from "./site-language";
import { Icon } from "./icon";
import "./catalog-entity-directory.css";

export async function CatalogEntityDirectory({ kind, parameters }: { kind: EntityKind; parameters: RouteQuery }) {
  const pathname = `/${kind}/`, destination = retiredFilterRedirect(pathname, parameters);
  if (destination) redirect(destination);
  const q = queryValue(parameters, "q"), page = catalogPageNumber(parameters), sort = queryValue(parameters, "sort");
  const role = kind === "contributors" ? queryValue(parameters, "role") || "author" : "";
  if (q.length > 120 || role.length > 32) notFound();
  const filter = new URLSearchParams({ q, role: role === "all" ? "" : role, sort, page: String(page) });
  let entities: EntityCollection;
  try { entities = await publicRequest<EntityCollection>(`catalog/entities/${kind}/?${filter}`); }
  catch (error) { if (error instanceof APIError && [400, 404].includes(error.status)) notFound(); throw error; }
  if (page > 1 && !entities.entries.length) notFound();
  const title = kind === "contributors" ? role === "author" ? "লেখক" : role === "all" ? "লেখক ও সহযোগী" : (Object.entries(contributorRoles).find(([value]) => value === role)?.[1] ?? entityLabels[kind]) : entityLabels[kind];
  return <section className="browse-directory"><header className="page-title"><h1><SiteText>{title}</SiteText></h1></header><CatalogBrowseNav current={pathname} />
    <form className="directory-toolbar" role="search"><div className="filter-search"><label className="visually-hidden" htmlFor="directory-query"><SiteText>নাম দিয়ে খুঁজুন</SiteText></label><Icon name="search" /><SiteInput placeholder="নাম দিয়ে খুঁজুন" id="directory-query" name="q" type="search" defaultValue={q} maxLength={120} /><button className="button"><SiteText>খুঁজুন</SiteText></button></div>
      {kind === "contributors" && <label><span className="visually-hidden"><SiteText>ভূমিকা</SiteText></span><SiteSelect aria-label="ভূমিকা" name="role" defaultValue={role}><option value="all"><SiteText>সব সহযোগী</SiteText></option>{Object.entries(contributorRoles).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</SiteSelect></label>}
      <label><span className="visually-hidden"><SiteText>তালিকা সাজানোর ধরন</SiteText></span><SiteSelect aria-label="তালিকা সাজানোর ধরন" name="sort" defaultValue={sort}>{Object.entries(directorySortLabels).filter(([value]) => kind !== "collections" || value.replace(/^-/, "") !== "catalog_code").map(([value, label]) => <option value={value} key={value}><SiteText>{label}</SiteText></option>)}</SiteSelect></label>
    </form>
    <ul className="entity-directory">{entities.entries.map(entity => <li key={entity.id}><Link href={`${catalogEntityPath(kind, entity.slug)}${role && role !== "all" ? `?role=${encodeURIComponent(role)}` : ""}`}><Icon name={kind === "contributors" ? "people" : "books"} /><strong>{entity.name}</strong><span>{entity.book_count !== undefined && <><SiteNumber value={entity.book_count} /> <SiteText>টি বই</SiteText></>}<Icon name="arrow" /></span></Link></li>)}</ul>
    {!entities.entries.length && <section className="empty-state"><Icon name="books" /><p><SiteText>{q ? "এই নামে কোনো তথ্য পাওয়া যায়নি।" : "প্রকাশিত বইয়ের লেখক ও বিভাগের তথ্য এখানে দেখা যাবে।"}</SiteText></p></section>}
    <CatalogPagination pathname={pathname} page={page} hasMore={entities.has_more} totalPages={entities.pagination?.page_count} query={q} filters={{ role, sort }} /></section>;
}
