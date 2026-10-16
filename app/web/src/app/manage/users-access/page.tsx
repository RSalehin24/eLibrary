import { AdminNumber, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedAccounts } from "@/api/types";
import { AdminPagination } from "@/components/admin-pagination";
import { accountStatuses } from "@/lib/access-status";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "ব্যবহারকারী ও অনুমতি" };

export default async function ManagedAccountsPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  await requireManagement("users-access"); const query = await searchParams;
  const search = queryValue(query, "q"), status = queryValue(query, "status") || "all";
  if (search.length > 200 || !Object.hasOwn(accountStatuses, status)) notFound();
  const parameters = new URLSearchParams({ q: search, status, page: String(routePageNumber(query)) });
  let accounts: ManagedAccounts;
  try { accounts = await sessionRequest<ManagedAccounts>(`manage/users/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><h1><AdminText>{"ব্যবহারকারী ও অনুমতি"}</AdminText></h1>
    <p><Link className="button" href="/manage/users-access/invite/"><AdminText>{"পাঠককে আমন্ত্রণ জানান"}</AdminText></Link></p>
    <form className="job-filters access-filters" method="get" role="search"><label htmlFor="account-query"><AdminText>{"নাম বা ইমেইল"}</AdminText></label><input id="account-query" name="q" defaultValue={search} maxLength={200} />
      <label htmlFor="account-status"><AdminText>{"হিসাবের অবস্থা"}</AdminText></label><select id="account-status" name="status" defaultValue={status}>{Object.entries(accountStatuses).map(([value, label]) => <option key={value} value={value}><AdminText>{label}</AdminText></option>)}</select><button className="button"><AdminText>{"হিসাব খুঁজুন"}</AdminText></button></form>
    <p className="muted"><AdminText>{"মোট "}</AdminText><AdminNumber value={accounts.pagination.total_count} /><AdminText>{"টি হিসাব"}</AdminText></p>
    <ul className="job-list">{accounts.entries.map((account) => <li className="job-card" key={account.id}><h2><Link className="text-link" href={`/manage/users-access/${account.id}/`}>{account.full_name || account.email}</Link></h2>
      <p lang="en" className="kindle-address">{account.email}</p><span className="status-label"><AdminText>{account.is_active ? "সক্রিয়" : "নিষ্ক্রিয়"}</AdminText></span><p className="muted"><AdminText>{"অনুমতি: "}</AdminText><AdminNumber value={account.grant_count} /> · <AdminText>{account.totp_required ? "দুই ধাপ আবশ্যক" : "দুই ধাপ ঐচ্ছিক"}</AdminText></p></li>)}</ul>
    {!accounts.entries.length && <p className="empty-state"><AdminText>{"এই নামে বা অবস্থায় কোনো হিসাব পাওয়া যায়নি।"}</AdminText></p>}
    <AdminPagination pagination={accounts.pagination} filter={parameters.toString()} label="ব্যবহারকারীর তালিকার পাতা" /></>;
}
