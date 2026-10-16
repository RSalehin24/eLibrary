import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { Automations } from "@/api/types";
import { AutomationsList } from "@/components/automations-list";
import { routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "স্বয়ংক্রিয় কাজ" };

export default async function AutomationsPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireManagement("automations");
  const filter = new URLSearchParams({ page: String(routePageNumber(await searchParams)) }).toString();
  let initial: Automations;
  try { initial = await sessionRequest<Automations>(`manage/automations/?${filter}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><h1><AdminText>{"স্বয়ংক্রিয় কাজ"}</AdminText></h1><p><AdminText>{"নির্ধারিত সময়ে নতুন উৎস আবিষ্কার করুন এবং নির্বাচিত সীমার মধ্যে বই প্রস্তুত করুন। প্রকাশের আগে সম্পাদকের পর্যালোচনা প্রয়োজন।"}</AdminText></p><Link className="button" href="/manage/automations/new/"><AdminText>{"নতুন সময়সূচি"}</AdminText></Link><AutomationsList initial={initial} filter={filter} /></>;
}
