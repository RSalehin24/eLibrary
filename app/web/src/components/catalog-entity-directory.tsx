import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { publicRequest } from "@/api/server";
import type { EntityCollection } from "@/api/types";
import { catalogEntityPath, entityLabels, type EntityKind } from "@/lib/catalog-entity";
import { contributorRoles } from "@/lib/contributor-roles";
import { catalogPageNumber, queryValue, type RouteQuery } from "@/lib/route-query";
import { CatalogPagination } from "./catalog-pagination";
import { CatalogBrowseNav } from "./catalog-browse-nav";
import { SiteText } from "./site-language";
import { Icon } from "./icon";

export async function CatalogEntityDirectory({ kind, parameters }: { kind: EntityKind; parameters: RouteQuery }) {
  const q = queryValue(parameters, "q"), role = queryValue(parameters, "role"), page = catalogPageNumber(parameters);
  if (q.length > 120 || role.length > 32) notFound();
  const filter = new URLSearchParams({ q, role, page: String(page) });
  let entities: EntityCollection;
  try { entities = await publicRequest<EntityCollection>(`catalog/entities/${kind}/?${filter}`); }
  catch (error) { if (error instanceof APIError && [400, 404].includes(error.status)) notFound(); throw error; }
  if (page > 1 && !entities.entries.length) notFound();
  const pathname = `/${kind}/`;
  return <><CatalogBrowseNav current={pathname} /><header className="page-title"><h1><SiteText>{entityLabels[kind]}</SiteText></h1>
    <p><SiteText>{"নাম বেছে নিয়ে সংশ্লিষ্ট বইয়ের তালিকা খুলুন।"}</SiteText></p></header>
    <form className="catalog-search" role="search"><label htmlFor="directory-query"><SiteText>{"নাম দিয়ে খুঁজুন"}</SiteText></label><div className="search-row"><input id="directory-query" name="q" defaultValue={q} maxLength={120} />
      {kind === "contributors" && <><label className="visually-hidden" htmlFor="directory-role"><SiteText>{"ভূমিকা"}</SiteText></label><select id="directory-role" name="role" defaultValue={role}><option value=""><SiteText>{"সব ভূমিকা"}</SiteText></option>{Object.entries(contributorRoles).map(([value, label]) => <option key={value} value={value}><SiteText>{label}</SiteText></option>)}</select></>}
      <button className="button"><Icon name="search" /><SiteText>{"খুঁজুন"}</SiteText></button></div></form>
    <ul className="entity-directory">{entities.entries.map(entity => <li key={entity.id}><Link href={`${catalogEntityPath(kind, entity.slug)}${role ? `?role=${encodeURIComponent(role)}` : ""}`}><Icon name={kind === "contributors" ? "people" : "books"} /><strong>{entity.name}</strong><span><SiteText>{"বই দেখুন"}</SiteText><Icon name="arrow" /></span></Link></li>)}</ul>
    {!entities.entries.length && <section className="empty-state"><Icon name="books" /><p><SiteText>{q ? "এই নামে কোনো তথ্য পাওয়া যায়নি।" : "প্রকাশিত বইয়ের লেখক ও বিভাগের তথ্য এখানে দেখা যাবে।"}</SiteText></p></section>}
    <CatalogPagination pathname={pathname} page={page} hasMore={entities.has_more} query={q} filters={role ? { role } : undefined} /></>;
}
