import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { SourceEntry } from "@/api/types";
import { SourceSummary } from "@/components/source-summary";
import { ProcessingAssets } from "@/components/processing-assets";
import { SourceProcessing } from "@/components/source-processing";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "উৎসের পরিচিতি" };

export default async function SourcePage({ params }: { params: Promise<{ identifier: string }> }) {
  const { identifier } = await params;
  if (!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(identifier)) notFound();
  await requireManagement("sources", `/manage/sources/${identifier}/`);
  let entry: SourceEntry;
  try { entry = await sessionRequest<SourceEntry>(`manage/sources/${identifier}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <div className="job-detail source-detail"><Link className="text-link" href="/manage/sources/"><AdminText>{"← উৎসের তালিকায় ফিরুন"}</AdminText></Link><h1><AdminText>{"উৎসের পরিচিতি"}</AdminText></h1>
    <section className="account-section"><SourceSummary entry={entry} /><p className="muted"><AdminText>{"এই পরিচিতি মূল উৎস থেকে সংগৃহীত। প্রকাশের আগে সম্পাদকীয় যাচাই প্রয়োজন।"}</AdminText></p>
      {entry.source_url ? <a className="text-link" href={entry.source_url} target="_blank" rel="noopener noreferrer"><AdminText>{"মূল উৎস খুলুন (নতুন ট্যাব) ↗"}</AdminText></a> : <p className="notice"><AdminText>{"মূল উৎসের ব্যবহারযোগ্য ঠিকানা পাওয়া যায়নি।"}</AdminText></p>}</section>
    <SourceProcessing entry={entry} />
    {entry.book && !entry.book.deleted_at && <ProcessingAssets slug={entry.book.slug} />}</div>;
}
