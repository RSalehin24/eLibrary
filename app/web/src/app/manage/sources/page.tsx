import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { SourceDiscoveryOptions, SourceEntries } from "@/api/types";
import { ManagedSources } from "@/components/managed-sources";
import { SourceDiscovery } from "@/components/source-discovery";
import { sourceStatuses } from "@/lib/source-status";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";
import Link from "next/link";
import { AdminText } from "@/components/admin-language";

export const metadata = { title: "বইয়ের উৎস" };

export default async function SourcesPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  const session = await requireManagement("sources"); const query = await searchParams;
  const search = queryValue(query, "q"), status = queryValue(query, "status") || "all";
  if (search.length > 200 || !Object.hasOwn(sourceStatuses, status)) notFound();
  const parameters = new URLSearchParams({ q: search, status, page: String(routePageNumber(query)) });
  let initial: SourceEntries;
  try { initial = await sessionRequest<SourceEntries>(`manage/sources/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  const options = await sessionRequest<SourceDiscoveryOptions>("manage/sources/discovery/");
  return <><div className="admin-page-heading"><div><h1><AdminText>বইয়ের উৎস</AdminText></h1><p className="muted"><AdminText>তালিকা থেকে বই নির্বাচন করে তৈরি করুন। EPUB নিজেও আপলোড করতে পারবেন।</AdminText></p></div>
    <div className="account-actions">{session.workspaces.can_create_books && <Link className="button button-quiet" href="/manage/books/new/"><AdminText>EPUB আপলোড</AdminText></Link>}<Link className="button button-quiet" href="/manage/jobs/"><AdminText>কাজের অগ্রগতি</AdminText></Link></div></div>
    <SourceDiscovery options={options} /><ManagedSources initial={initial} filter={parameters.toString()} /></>;
}
