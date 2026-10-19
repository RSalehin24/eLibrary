import { localizeMetadata } from "@/lib/metadata-language";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { BackgroundJobCollection } from "@/api/types";
import { ManagedJobs } from "@/components/managed-jobs";
import { jobFilterKeys, savedQueueFilter } from "@/lib/job-filters";
import { requireManagement } from "@/lib/workspace-session";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { AdminText } from "@/components/admin-language";

export async function generateMetadata() { return localizeMetadata({ title: "কাজ পরিচালনা" }); }

export default async function JobsPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireManagement("jobs");
  const query = await searchParams;
  const page = routePageNumber(query);
  const values = savedQueueFilter(Object.fromEntries(jobFilterKeys.map((key) => [key, queryValue(query, key)])));
  if (!values) notFound();
  const parameters = new URLSearchParams({ ...values, page: String(page) });
  let initial: BackgroundJobCollection;
  try { initial = await sessionRequest<BackgroundJobCollection>(`manage/jobs/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><h1><AdminText>কাজ পরিচালনা</AdminText></h1><ManagedJobs key={parameters.toString()} initial={initial} filter={parameters.toString()} /></>;
}
