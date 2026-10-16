import Link from "next/link";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { KindleOperation as Operation } from "@/api/types";
import { KindleOperation } from "@/components/kindle-operation";
import { requireReader } from "@/lib/workspace-session";

export const metadata = { title: "কিন্ডল অনুরোধের অবস্থা" };

export default async function KindleOperationPage({ params }: { params: Promise<{ identifier: string }> }) {
  const { identifier } = await params;
  await requireReader(`/kindle/operations/${encodeURIComponent(identifier)}/`);
  let operation: Operation;
  try { operation = await sessionRequest<Operation>(`delivery/operations/${encodeURIComponent(identifier)}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href="/kindle/">← অনুরোধের তালিকায় ফিরুন</Link><h1>কিন্ডল অনুরোধের অবস্থা</h1><KindleOperation initial={operation} /></>;
}
