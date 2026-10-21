import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedEntities } from "@/api/types";
import { contributorRoles } from "@/lib/contributor-roles";
import { entityFilters, entityLabels, type EntityKind } from "@/lib/catalog-entity";
import { catalogStateLabel } from "@/lib/catalog-state";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";
import { AdminNumber, AdminText } from "./admin-language";
import { AdminPagination } from "./admin-pagination";
import { EntityNavigation } from "./entity-navigation";
import { Icon } from "./icon";

export async function ManagedEntityList({ kind, parameters }: { kind: EntityKind; parameters: RouteQuery }) {
  const session = await requireManagement("books", `/manage/entities/${kind}/`);
  const page = routePageNumber(parameters), query = queryValue(parameters, "q"), role = queryValue(parameters, "role");
  if (query.length > 120) notFound();
  const filter = new URLSearchParams({ q: query });
  if (role) filter.set("role", role);
  let entities: ManagedEntities;
  try { entities = await sessionRequest<ManagedEntities>(`manage/entities/${kind}/?${filter}&page=${page}`); }
  catch (error) { if (error instanceof APIError && [400, 404].includes(error.status)) notFound(); throw error; }
  return <><header className="catalog-list-heading"><div><h1><AdminText>{entityLabels[kind]}</AdminText></h1>
</div>
    {session.workspaces.can_create_books && <Link className="button" href={`/manage/entities/${kind}/new/`}><Icon name="plus" /><AdminText>{"পরিচিতি তৈরি করুন"}</AdminText></Link>}</header><EntityNavigation current={kind} />
    <form className="catalog-search" role="search"><label htmlFor="entity-query"><AdminText>{"নাম বা বিকল্প নাম খুঁজুন"}</AdminText></label>
      <div className="search-row"><input type="search" id="entity-query" name="q" defaultValue={query} maxLength={120} />
        {kind === "contributors" && <><label className="visually-hidden" htmlFor="entity-role"><AdminText>{"ভূমিকা"}</AdminText></label><select id="entity-role" name="role" defaultValue={role}><option value=""><AdminText>{"সব ভূমিকা"}</AdminText></option>
          {Object.entries(contributorRoles).map(([value, label]) => <option key={value} value={value}><AdminText>{label}</AdminText></option>)}</select></>}
        <button className="button"><Icon name="search" /><AdminText>{"খুঁজুন"}</AdminText></button></div></form>
    <p className="muted"><AdminText>{"মোট "}</AdminText><AdminNumber value={entities.pagination.total_count} /><AdminText>{"টি পরিচিতি"}</AdminText></p>
    <ul className="management-list entity-results">{entities.entries.map(entity => <li key={entity.id}><div className="entity-result-name">
      <Icon name={kind === "contributors" ? "people" : kind === "categories" ? "tags" : "books"} /><h2><Link className="text-link" href={`/manage/entities/${kind}/${entity.id}/`}>{entity.name}</Link></h2>
      {entity.state && <span className="status-label"><AdminText>{catalogStateLabel(entity.state)}</AdminText></span>}</div>
      <div className="editorial-actions"><Link className="button button-quiet" href={`/manage/books/?${new URLSearchParams({ [entityFilters[kind]]: entity.slug, label: entity.name, ...(kind === "contributors" && role ? { contributor_role: role } : {}) })}`}><Icon name="books" /><AdminText>{"সংশ্লিষ্ট বই দেখুন"}</AdminText></Link>
        <Link className="button button-quiet" href={`/manage/entities/${kind}/${entity.id}/`}><Icon name="edit" /><AdminText>{"সম্পাদনা করুন"}</AdminText></Link></div>
    </li>)}</ul>
    {!entities.entries.length && <section className="empty-state"><Icon name="people" /><h2><AdminText>{query ? "এই নামে কোনো তথ্য পাওয়া যায়নি।" : "এখনও কোনো তথ্য যোগ করা হয়নি।"}</AdminText></h2>
      <p><AdminText>{query ? "নাম বদলে খুঁজুন অথবা সম্পূর্ণ তালিকা দেখুন।" : "উপরের যোগ করুন বাটন থেকে নতুন তথ্য যোগ করুন।"}</AdminText></p>
      {query && <Link className="button button-quiet" href={`/manage/entities/${kind}/`}><Icon name="refresh" /><AdminText>{"সম্পূর্ণ তালিকা দেখুন"}</AdminText></Link>}</section>}
    <AdminPagination pagination={entities.pagination} filter={filter.toString()} label="পরিচিতির তালিকার পাতা" /></>;
}
