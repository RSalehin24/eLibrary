import { localizeMetadata } from "@/lib/metadata-language";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { SourceDiscoveryOptions, SourceEntries } from "@/api/types";
import { ManagedSources } from "@/components/managed-sources";
import { SourceDiscovery } from "@/components/source-discovery";
import { ProcessAllSources } from "@/components/process-all-sources";
import { SourceScheduling } from "@/components/source-scheduling";
import type { CatalogProcessingOptions, Automations } from "@/api/types";
import { sourceStatuses } from "@/lib/source-status";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";
import Link from "next/link";
import { AdminText } from "@/components/admin-language";
import { Icon } from "@/components/icon";

export async function generateMetadata() { return localizeMetadata({ title: "বইয়ের উৎস" }); }

export default async function SourcesPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  const session = await requireManagement("sources"); const query = await searchParams;
  const search = queryValue(query, "q"), status = queryValue(query, "status") || "all";
  if (search.length > 200 || !Object.hasOwn(sourceStatuses, status)) notFound();
  const parameters = new URLSearchParams({ q: search, status, page: String(routePageNumber(query)) });
  let initial: SourceEntries;
  try { initial = await sessionRequest<SourceEntries>(`manage/sources/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  const [options, processing, automations] = await Promise.all([sessionRequest<SourceDiscoveryOptions>("manage/sources/discovery/"), sessionRequest<CatalogProcessingOptions>("manage/sources/process-all/"), sessionRequest<Automations>("manage/automations/?page=1")]);
  return <><div className="admin-page-heading"><div><h1><AdminText>বই তৈরি</AdminText></h1><p className="muted"><AdminText>তালিকা থেকে বই বেছে নিন, তৈরি করুন, তারপর ফাইল যাচাই করে প্রকাশ করুন।</AdminText></p></div>
    <Link className="text-link" href="/manage/jobs/"><AdminText>কাজের অগ্রগতি</AdminText></Link></div>
    <div className="admin-controls"><SourceDiscovery options={options} /><ProcessAllSources initial={processing} /><SourceScheduling initial={automations} />{session.workspaces.can_create_books && <Link className="button button-quiet admin-main-action" href="/manage/books/new/"><Icon name="upload" /><AdminText>নিজে বই যোগ করুন</AdminText></Link>}</div><ManagedSources initial={initial} filter={parameters.toString()} /></>;
}
