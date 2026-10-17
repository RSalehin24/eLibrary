import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { BackgroundJobDetail } from "@/api/types";
import { JobDetail } from "@/components/job-detail";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "কাজের অবস্থা" }); }

export default async function JobPage({ params }: { params: Promise<{ identifier: string }> }) {
  const { identifier } = await params;
  await requireManagement("jobs", `/manage/jobs/${identifier}/`);
  let job: BackgroundJobDetail;
  try { job = await sessionRequest<BackgroundJobDetail>(`manage/jobs/${encodeURIComponent(identifier)}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href="/manage/jobs/"><AdminText>{"← কাজের তালিকায় ফিরুন"}</AdminText></Link><h1><AdminText>{"কাজের অবস্থা"}</AdminText></h1><JobDetail initial={job} /></>;
}
