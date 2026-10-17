import { localizeMetadata } from "@/lib/metadata-language";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { SourceEntry } from "@/api/types";
import { SourceWorkspace } from "@/components/source-workspace";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "উৎসের পরিচিতি" }); }

export default async function SourcePage({ params }: { params: Promise<{ identifier: string }> }) {
  const { identifier } = await params;
  if (!/^[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}$/i.test(identifier)) notFound();
  await requireManagement("sources", `/manage/sources/${identifier}/`);
  let entry: SourceEntry;
  try { entry = await sessionRequest<SourceEntry>(`manage/sources/${identifier}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <SourceWorkspace initial={entry} />;
}
