import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedAccount, ManagedGrants } from "@/api/types";
import { ManagedAccountWorkspace } from "@/components/managed-account-workspace";
import { routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "হিসাব ও অনুমতি পরিচালনা" }); }

export default async function ManagedAccountPage({ params, searchParams }: { params: Promise<{ identifier: string }>; searchParams: Promise<RouteQuery> }) {
  const raw = (await params).identifier; if (!/^[1-9][0-9]*$/.test(raw) || !Number.isSafeInteger(Number(raw))) notFound();
  await requireManagement("users-access", `/manage/users-access/${raw}/`);
  const parameters = new URLSearchParams({ page: String(routePageNumber(await searchParams)) });
  let account: ManagedAccount, grants: ManagedGrants;
  try { [account, grants] = await Promise.all([sessionRequest<ManagedAccount>(`manage/users/${raw}/`), sessionRequest<ManagedGrants>(`manage/users/${raw}/grants/?${parameters}`)]); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href="/manage/users-access/"><AdminText>{"← ব্যবহারকারীর তালিকায় ফিরুন"}</AdminText></Link><ManagedAccountWorkspace key={`${raw}:${parameters}`} initial={account} initialGrants={grants} filter={parameters.toString()} /></>;
}
