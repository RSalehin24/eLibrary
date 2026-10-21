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
import { AdminNavigation, AdminText } from "@/components/admin-language";
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
  const [options, processing, automations] = await Promise.all([sessionRequest<SourceDiscoveryOptions>("manage/sources/discovery/"), sessionRequest<CatalogProcessingOptions>("manage/sources/process-all/"), session.workspaces.management_sections.includes("automations") ? sessionRequest<Automations>("manage/automations/?page=1") : null]);
  return <section className="book-creation-center"><header className="admin-page-heading"><div><h1><AdminText>বই তৈরি</AdminText></h1></div>
    {session.workspaces.management_sections.includes("jobs") && <Link className="text-link" href="/manage/jobs/"><Icon name="jobs" /><AdminText>কাজের অবস্থা</AdminText></Link>}</header>
    <div className="admin-controls source-creation-actions"><SourceDiscovery options={options} /><ProcessAllSources initial={processing} />
      {session.workspaces.can_create_books && <Link className="button button-quiet admin-main-action" href="/manage/books/new/"><Icon name="upload" /><AdminText>EPUB আপলোড</AdminText></Link>}
      {automations && <SourceScheduling initial={automations} />}</div>
    <AdminNavigation className="admin-local-tabs" label="বই তৈরির তালিকা"><Link href="/manage/sources/" aria-current="page"><Icon name="source" /><AdminText>ওয়েবসাইটের বই</AdminText></Link><Link href="/manage/unfinished/"><Icon name="read" /><AdminText>অসম্পূর্ণ বই</AdminText></Link></AdminNavigation>
    <ManagedSources initial={initial} filter={parameters.toString()} /></section>;
}
