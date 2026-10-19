import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import { sessionRequest } from "@/api/server";
import type { KindleCollection } from "@/api/types";
import { APIError } from "@/api/http";
import { notFound } from "next/navigation";
import { kindleHistoryKeys, kindleHistoryQuery } from "@/lib/kindle-history";
import { queryValue, type RouteQuery } from "@/lib/route-query";
import { KindleHistory } from "@/components/kindle-history";
import { KindleHistoryFilters } from "@/components/kindle-history-filters";
import { requireReader } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "কিন্ডলে পাঠানোর অনুরোধ" }); }

export default async function KindlePage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireReader("/kindle/");
  const parameters = await searchParams;
  const filters = Object.fromEntries(kindleHistoryKeys.map((key) => [key, queryValue(parameters, key)]));
  if (Object.values(filters).some((value) => value.length > 255)) notFound();
  const filter = kindleHistoryQuery(filters);
  let initial: KindleCollection;
  try { initial = await sessionRequest<KindleCollection>(`me/kindle/?${filter}`); }
  catch (error) { if (error instanceof APIError && error.status === 400) notFound(); throw error; }
  return <><p className="eyebrow"><SiteText>{"আপনার ব্যক্তিগত পাঠাগার"}</SiteText></p><h1><SiteText>{"কিন্ডলে পাঠানোর অনুরোধ"}</SiteText></h1><KindleHistoryFilters key={filter} initial={filters} /><KindleHistory key={filter} initial={initial} filter={filter} /></>;
}
