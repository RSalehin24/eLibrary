"use client";

import { SiteSection } from "@/components/site-language";

import { AdminNumber, AdminText } from "@/components/admin-language";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { readManagedAccount, readManagedGrants } from "@/api/managed-access";
import type { ManagedAccount, ManagedGrant, ManagedGrants } from "@/api/types";
import { ManagedAccountForm } from "./managed-account-form";
import { ManagedGrantForm } from "./managed-grant-form";
import { ManagedGrantCard } from "./managed-grant-card";
import { AdminPagination } from "./admin-pagination";
import { AccountMailHistory } from "./account-mail-history";

export function ManagedAccountWorkspace({ initial, initialGrants, filter }: { initial: ManagedAccount; initialGrants: ManagedGrants; filter: string }) {
  const client = useQueryClient();
  const accountKey = ["private", "access", "account", initial.id];
  const account = useQuery({ queryKey: accountKey, queryFn: ({ signal }) => readManagedAccount(initial.id, signal), initialData: initial, refetchOnWindowFocus: false });
  const grants = useQuery({ queryKey: [...accountKey, "grants", filter], queryFn: ({ signal }) => readManagedGrants(initial.id, filter, signal), initialData: initialGrants, refetchOnWindowFocus: false });
  async function onAccountSaved(updated: ManagedAccount) { client.setQueryData(accountKey, updated); await client.invalidateQueries({ queryKey: ["private", "access", "accounts"] }); }
  async function onGrantSaved(updated: ManagedGrant) {
    client.setQueryData([...accountKey, "grants", filter], (previous: ManagedGrants | undefined) => previous ? { ...previous, entries: previous.entries.map((grant) => grant.id === updated.id ? updated : grant) } : previous);
    await Promise.all([client.invalidateQueries({ queryKey: [...accountKey, "grants"] }), client.invalidateQueries({ queryKey: accountKey, exact: true })]);
  }
  return <div className="account-settings"><h1>{account.data.full_name || account.data.email}</h1>
    {(account.isError || grants.isError) && <p className="field-error" role="alert"><AdminText>{"বর্তমান তথ্য পাওয়া যায়নি। ফর্ম জমা দেওয়ার আগে পাতা আবার খুলুন।"}</AdminText></p>}
    <p className="muted"><AdminText>{"প্রবেশ: "}</AdminText><AdminText>{account.data.is_active ? "সক্রিয়" : "নিষ্ক্রিয়"}</AdminText><AdminText>{" · দুই ধাপ: "}</AdminText><AdminText>{account.data.has_totp_enabled ? "চালু" : "প্রস্তুতি বাকি"}</AdminText></p>
    {account.data.can_edit ? <><ManagedAccountForm account={account.data} onSaved={onAccountSaved} /><ManagedGrantForm account={account.data} onSaved={onGrantSaved} /></> : <p className="notice"><AdminText>{"নিজের হিসাব বা এই সংরক্ষিত প্রশাসনিক হিসাব এখান থেকে বদলানো যাবে না।"}</AdminText></p>}
    {account.data.can_edit && <AccountMailHistory account={account.data} />}
    <SiteSection aria-label="এই হিসাবের অনুমতি"><h2><AdminText>{"অনুমতির তালিকা"}</AdminText></h2><p className="muted"><AdminText>{"মোট "}</AdminText><AdminNumber value={grants.data.pagination.total_count} /><AdminText>{"টি অনুমতি। বইয়ের মালিকানা এই তালিকার থেকে আলাদা।"}</AdminText></p>
      <ul className="job-list">{grants.data.entries.map((grant) => <ManagedGrantCard key={grant.id} grant={grant} editable={account.data.can_edit} onSaved={onGrantSaved} />)}</ul>
      {!grants.data.entries.length && <p className="empty-state"><AdminText>{"এখনো কোনো অনুমতি দেওয়া হয়নি।"}</AdminText></p>}
      <AdminPagination pagination={grants.data.pagination} filter={filter} label="অনুমতির তালিকার পাতা" /></SiteSection></div>;
}
