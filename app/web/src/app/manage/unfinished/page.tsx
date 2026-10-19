import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import type { SourceDiscoveryOptions, SourceEntries } from "@/api/types";
import { localizeMetadata } from "@/lib/metadata-language";
import { requireManagement } from "@/lib/workspace-session";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { sourceStatuses } from "@/lib/source-status";
import { ManagedSources } from "@/components/managed-sources";
import { SourceDiscovery } from "@/components/source-discovery";
import { AdminNavigation, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { Icon } from "@/components/icon";

export async function generateMetadata() { return localizeMetadata({ title: "অসম্পূর্ণ বই" }); }

export default async function UnfinishedBooksPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireManagement("sources", "/manage/unfinished/");
  const query = await searchParams, search = queryValue(query, "q"), status = queryValue(query, "status") || "all";
  if (search.length > 200 || !Object.hasOwn(sourceStatuses, status)) notFound();
  const parameters = new URLSearchParams({ catalog_scope: "unfinished", q: search, status, page: String(routePageNumber(query)) });
  const [initial, options] = await Promise.all([
    sessionRequest<SourceEntries>(`manage/sources/?${parameters}`),
    sessionRequest<SourceDiscoveryOptions>("manage/sources/discovery/?catalog_scope=unfinished"),
  ]);
  return <><header className="admin-page-heading unfinished-books-heading"><div><h1><AdminText>{"অসম্পূর্ণ বই"}</AdminText></h1>
    <p className="muted"><AdminText>{"মূল ওয়েবসাইটে অসম্পূর্ণ হিসেবে রাখা বই। সেখানে নতুন অংশ যোগ হলে তালিকা হালনাগাদ করে বইয়ের নতুন সংস্করণ তৈরি করতে পারবেন।"}</AdminText></p>
    <p className="muted"><AdminText>তালিকা হালনাগাদ করলে ওয়েবসাইটের সূচি পরীক্ষা হবে। পরিবর্তন পাওয়া বইয়ে “আপডেট আছে” দেখাবে।</AdminText></p>
    <AdminNavigation className="catalog-browse-nav" label="আপডেটের তালিকা"><Link className="button button-quiet" href="/manage/unfinished/" aria-current={status === "all" ? "page" : undefined}><Icon name="books" /><AdminText>সব অসম্পূর্ণ বই</AdminText></Link><Link className="button button-quiet" href="/manage/unfinished/?status=updated" aria-current={status === "updated" ? "page" : undefined}><Icon name="refresh" /><AdminText>আপডেট আছে</AdminText></Link></AdminNavigation></div></header>
    <div className="admin-controls"><SourceDiscovery options={options} catalogScope="unfinished" /></div>
    <ManagedSources initial={initial} filter={parameters.toString()} /></>;
}
