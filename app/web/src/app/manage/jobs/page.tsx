import { localizeMetadata } from "@/lib/metadata-language";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { BackgroundJobCollection } from "@/api/types";
import { ManagedJobs } from "@/components/managed-jobs";
import { jobStates } from "@/lib/job-status";
import { requireManagement } from "@/lib/workspace-session";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { AdminText } from "@/components/admin-language";

export async function generateMetadata() { return localizeMetadata({ title: "কাজ পরিচালনা" }); }

export default async function JobsPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireManagement("jobs");
  const query = await searchParams;
  const page = routePageNumber(query), state = queryValue(query, "state");
  if (state && !Object.hasOwn(jobStates, state)) notFound();
  const parameters = new URLSearchParams({ page: String(page) });
  if (state) parameters.set("state", state);
  for (const key of ["automation_run", "parent_job"]) {
    const identifier = queryValue(query, key);
    if (!identifier) continue;
    if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(identifier)) notFound();
    parameters.set(key, identifier);
  }
  let initial: BackgroundJobCollection;
  try { initial = await sessionRequest<BackgroundJobCollection>(`manage/jobs/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><h1><AdminText>কাজ পরিচালনা</AdminText></h1><ManagedJobs initial={initial} filter={parameters.toString()} /></>;
}
