import { AdminNumber, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedEntities } from "@/api/types";
import { AdminPagination } from "@/components/admin-pagination";
import { entityLabels } from "@/lib/catalog-entity";
import { managedEntityKind } from "@/lib/managed-entity";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "পরিচিতির তালিকা" };

export default async function ManagedEntityListPage({ params, searchParams }: { params: Promise<{ kind: string }>; searchParams: Promise<RouteQuery> }) {
  const kind = managedEntityKind((await params).kind);
  const session = await requireManagement("books", `/manage/entities/${kind}/`);
  const parameters = await searchParams, page = routePageNumber(parameters), query = queryValue(parameters, "q");
  if (query.length > 120) notFound();
  const filter = new URLSearchParams({ q: query });
  let entities: ManagedEntities;
  try { entities = await sessionRequest<ManagedEntities>(`manage/entities/${kind}/?${filter}&page=${page}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href="/manage/entities/"><AdminText>{"← পরিচিতি পরিচালনায় ফিরুন"}</AdminText></Link><h1><AdminText>{entityLabels[kind]}</AdminText></h1>
    {session.workspaces.can_create_books && <Link className="button" href={`/manage/entities/${kind}/new/`}><AdminText>{"পরিচিতি তৈরি করুন"}</AdminText></Link>}
    <form className="catalog-search" role="search"><label htmlFor="entity-query"><AdminText>{"নাম বা বিকল্প নাম খুঁজুন"}</AdminText></label>
      <div className="search-row"><input id="entity-query" name="q" defaultValue={query} maxLength={120} /><button className="button"><AdminText>{"খুঁজুন"}</AdminText></button></div></form>
    <p className="muted"><AdminText>{"মোট "}</AdminText><AdminNumber value={entities.pagination.total_count} /><AdminText>{"টি পরিচিতি"}</AdminText></p>
    <ul className="management-list">{entities.entries.map((entity) => <li key={entity.id}><div>
      <h2><Link className="text-link" href={`/manage/entities/${kind}/${entity.id}/`}>{entity.name}</Link></h2>
      <p className="muted"><AdminText>{entity.editorial_reviewed_at ? "পর্যালোচিত" : "পর্যালোচনা প্রয়োজন"}</AdminText></p></div>
      {entity.state && <span className="status-label">{entity.state === "published" ? "প্রকাশিত" : entity.state === "archived" ? "প্রত্যাহৃত" : "খসড়া"}</span>}
    </li>)}</ul>
    {!entities.entries.length && <p className="empty-state"><AdminText>{"আপনার পরিচালনার তালিকায় এই নামে কোনো পরিচিতি নেই।"}</AdminText></p>}
    <AdminPagination pagination={entities.pagination} filter={filter.toString()} label="পরিচিতির তালিকার পাতা" />
  </>;
}
