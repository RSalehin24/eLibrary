import { AdminDirectoryFilters } from "@/components/admin-directory-filters";
import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { Automations } from "@/api/types";
import { AutomationsList } from "@/components/automations-list";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";
import { automationFrequencies } from "@/lib/automation-status";
import { AdminPageHeader } from "@/components/admin-page-header";
import { Icon } from "@/components/icon";

export async function generateMetadata() { return localizeMetadata({ title: "স্বয়ংক্রিয় কাজ" }); }

export default async function AutomationsPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireManagement("automations");
  const query = await searchParams;
  const search = queryValue(query, "q"), enabled = queryValue(query, "enabled") || "all", frequency = queryValue(query, "frequency"), sort = queryValue(query, "sort") || "name";
  if (search.length > 150 || !["all", "enabled", "disabled"].includes(enabled) || frequency && !Object.hasOwn(automationFrequencies, frequency) || !["name", "next_run", "-next_run"].includes(sort)) notFound();
  const filter = new URLSearchParams({ q: search, enabled, frequency, sort, page: String(routePageNumber(query)) }).toString();
  let initial: Automations;
  try { initial = await sessionRequest<Automations>(`manage/automations/?${filter}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><AdminPageHeader title="সময়সূচি" description="নিয়মিত তালিকা হালনাগাদ করুন, নতুন বই তৈরি করুন এবং অসম্পূর্ণ বইয়ের পরিবর্তন পরীক্ষা করুন। স্বয়ংক্রিয় যাচাই সফল হলে বই প্রকাশিত হবে।" icon="schedule">
    <Link className="button" href="/manage/automations/new/"><Icon name="plus" /><AdminText>{"নতুন সময়সূচি"}</AdminText></Link>
    </AdminPageHeader>
    <AdminDirectoryFilters pathname="/manage/automations/" search={{ label: "সময়সূচি খুঁজুন", value: search, maxLength: 150 }} active={!!search || enabled !== "all" || !!frequency || sort !== "name"}
      primary={[{ name: "enabled", label: "অবস্থা", value: enabled, options: { all: "সব সময়সূচি", enabled: "সক্রিয়", disabled: "বন্ধ" } }]}
      advanced={[{ name: "frequency", label: "কত দিন পরপর চলবে", value: frequency, options: { "": "সব সময়সূচি", ...automationFrequencies } }, { name: "sort", label: "সাজান", value: sort, options: { name: "নাম: অ থেকে হ", next_run: "পরের কাজ আগে", "-next_run": "পরের কাজ পরে" } }]} />
    <AutomationsList initial={initial} filter={filter} /></>;
}
