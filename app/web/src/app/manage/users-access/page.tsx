import { AdminDirectoryFilters } from "@/components/admin-directory-filters";
import { localizeMetadata } from "@/lib/metadata-language";
import { AdminNumber, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedAccounts } from "@/api/types";
import { AdminPagination } from "@/components/admin-pagination";
import { accountSorts, accountStatuses } from "@/lib/access-status";
import { queryValue, routePageNumber, type RouteQuery } from "@/lib/route-query";
import { requireManagement } from "@/lib/workspace-session";
import { AdminPageHeader } from "@/components/admin-page-header";
import { ManagedAccountsTable } from "@/components/managed-accounts-table";
import { Icon } from "@/components/icon";

export async function generateMetadata() { return localizeMetadata({ title: "ব্যবহারকারী ও অনুমতি" }); }

export default async function ManagedAccountsPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  const session = await requireManagement("users-access"); const query = await searchParams;
  const search = queryValue(query, "q"), status = queryValue(query, "status") || "all";
  const sort = queryValue(query, "sort") || "name_asc";
  if (search.length > 200 || !Object.hasOwn(accountStatuses, status) || !Object.hasOwn(accountSorts, sort)) notFound();
  const parameters = new URLSearchParams({ q: search, status, sort, page: String(routePageNumber(query)) });
  let accounts: ManagedAccounts;
  try { accounts = await sessionRequest<ManagedAccounts>(`manage/users/?${parameters}`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><AdminPageHeader title="ব্যবহারকারী" description="অ্যাকাউন্ট খুঁজুন, প্রবেশাধিকার নিয়ন্ত্রণ করুন এবং বই পড়ার অনুমতি দিন।" icon="people">
    <Link className="button" href="/manage/users-access/invite/"><Icon name="plus" /><AdminText>{session.user?.is_superuser ? "পাঠক যোগ করুন" : "পাঠককে আমন্ত্রণ জানান"}</AdminText></Link>
    </AdminPageHeader>
    <AdminDirectoryFilters pathname="/manage/users-access/" search={{ label: "নাম, ইমেইল বা অনুমতি", value: search, maxLength: 200 }} active={!!search || status !== "all" || sort !== "name_asc"}
      primary={[{ name: "status", label: "হিসাবের অবস্থা", value: status, options: accountStatuses }, { name: "sort", label: "অ্যাকাউন্টের তালিকা সাজান", value: sort, options: accountSorts }]} />

    <section className="admin-list-results" aria-labelledby="account-results-heading"><header className="admin-results-heading"><h2 id="account-results-heading"><AdminText>{"অ্যাকাউন্টের তালিকা"}</AdminText><span className="count-badge"><AdminNumber value={accounts.pagination.total_count} /></span></h2>
      <p><AdminText>{"নাম বা পরিচালনা করুন বাটন থেকে অ্যাকাউন্ট খুলুন।"}</AdminText></p></header>
    {accounts.entries.length ? <ManagedAccountsTable accounts={accounts} /> : <div className="admin-list-empty"><Icon name="people" size={32} /><h2><AdminText>{"এই নামে বা অবস্থায় কোনো হিসাব পাওয়া যায়নি।"}</AdminText></h2><p><AdminText>{"ফিল্টার বদলে বা কম শর্ত দিয়ে আবার খুঁজুন।"}</AdminText></p><Link className="button button-quiet" href="/manage/users-access/"><AdminText>{"সব ফিল্টার মুছুন"}</AdminText></Link></div>}
    </section>
    <AdminPagination pagination={accounts.pagination} filter={parameters.toString()} label="ব্যবহারকারীর তালিকার পাতা" /></>;
}
