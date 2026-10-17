import { localizeMetadata } from "@/lib/metadata-language";
import { AdminDate, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { AutomationRuns, SourceAutomation } from "@/api/types";
import { AutomationForm } from "@/components/automation-form";
import { AutomationRunHistory } from "@/components/automation-runs";
import { routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "সময়সূচি ও চলার ইতিহাস" }); }

export default async function AutomationPage({ params, searchParams }: { params: Promise<{ identifier: string }>; searchParams: Promise<RouteQuery> }) {
  await requireManagement("automations");
  const { identifier } = await params;
  const filter = new URLSearchParams({ page: String(routePageNumber(await searchParams)) }).toString();
  let automation: SourceAutomation, runs: AutomationRuns;
  try { [automation, runs] = await Promise.all([sessionRequest<SourceAutomation>(`manage/automations/${identifier}/`), sessionRequest<AutomationRuns>(`manage/automations/${identifier}/runs/?${filter}`)]); }
  catch (error) { if (error instanceof APIError && [400, 404].includes(error.status)) notFound(); throw error; }
  return <><Link className="text-link" href="/manage/automations/"><AdminText>{"← সময়সূচিতে ফিরুন"}</AdminText></Link><h1>{automation.name}</h1><p><AdminText>{automation.enabled ? "সক্রিয়" : "বন্ধ"}</AdminText><AdminText>{" · পরের নির্ধারিত সময়: "}</AdminText><AdminDate value={automation.next_run_at} /></p><p className="muted"><AdminText>{"যাঁর অনুমতিতে চলবে: "}</AdminText>{automation.run_as_name}</p><AutomationForm automation={automation} /><AutomationRunHistory id={automation.id} initial={runs} filter={filter} /></>;
}
