import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { KindleOperation as Operation } from "@/api/types";
import { KindleOperation } from "@/components/kindle-operation";
import { requireReader } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "কিন্ডল অনুরোধের অবস্থা" }); }

export default async function KindleOperationPage({ params }: { params: Promise<{ identifier: string }> }) {
  const { identifier } = await params;
  await requireReader(`/kindle/operations/${encodeURIComponent(identifier)}/`);
  let operation: Operation;
  try { operation = await sessionRequest<Operation>(`delivery/operations/${encodeURIComponent(identifier)}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href="/kindle/"><SiteText>{"← অনুরোধের তালিকায় ফিরুন"}</SiteText></Link><h1><SiteText>{"কিন্ডল অনুরোধের অবস্থা"}</SiteText></h1><KindleOperation initial={operation} /></>;
}
