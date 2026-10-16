import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { AccountMailOperation } from "@/api/types";
import { AccountMailDetail } from "@/components/account-mail-detail";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "আমন্ত্রণের অবস্থা" };

export default async function MailOperationPage({ params }: { params: Promise<{ identifier: string }> }) {
  const { identifier } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(identifier)) notFound();
  await requireManagement("users-access", `/manage/users-access/mail/${identifier}/`);
  let initial: AccountMailOperation;
  try { initial = await sessionRequest<AccountMailOperation>(`manage/mail/${identifier}/`); }
  catch (error) { if (error instanceof APIError && [403, 404].includes(error.status)) notFound(); throw error; }
  return <><Link className="text-link" href="/manage/users-access/"><AdminText>{"← ব্যবহারকারীর তালিকায় ফিরুন"}</AdminText></Link><AccountMailDetail initial={initial} /></>;
}
