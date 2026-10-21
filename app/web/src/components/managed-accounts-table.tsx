"use client";

import Link from "next/link";
import type { ManagedAccounts } from "@/api/types";
import { useAdminLanguage } from "./admin-language";
import { Icon } from "./icon";

export function ManagedAccountsTable({ accounts }: { accounts: ManagedAccounts }) {
  const { t, number } = useAdminLanguage();
  return <div className="admin-data-list"><table className="admin-data-table account-directory" role="table">
    <thead><tr><th scope="col">{t("ব্যবহারকারী")}</th><th scope="col">{t("হিসাবের অবস্থা")}</th><th scope="col">{t("নিরাপত্তা")}</th><th scope="col">{t("অনুমতি")}</th><th scope="col"><span className="visually-hidden">{t("করণীয়")}</span></th></tr></thead>
    <tbody>{accounts.entries.map(account => <tr key={account.id}>
      <th scope="row"><div className="admin-record-identity"><span className="admin-record-icon"><Icon name="people" size={22} /></span><div className="admin-record-copy"><Link href={`/manage/users-access/${account.id}/`}>{account.full_name || account.email}</Link>
        {account.full_name && <span className="admin-record-secondary" lang="en">{account.email}</span>}
        {(account.is_staff || account.is_superuser) && <span className="admin-role-label">{t(account.is_superuser ? "সুপার অ্যাডমিন" : "অ্যাডমিন")}</span>}
      </div></div></th>
      <td data-label={t("হিসাবের অবস্থা")}><span className="admin-status" data-status={account.is_active ? "active" : "paused"}><span aria-hidden="true" />{t(account.is_active ? "সক্রিয়" : "নিষ্ক্রিয়")}</span>
        {account.email_setup_pending && <small>{t("অ্যাকাউন্ট সেটআপ বাকি")}</small>}</td>
      <td data-label={t("নিরাপত্তা")}><span className="admin-security-state"><Icon name={account.has_totp_enabled ? "check" : "warning"} />{t(account.has_totp_enabled ? "দুই ধাপের নিরাপত্তা চালু" : "দুই ধাপের নিরাপত্তা বন্ধ")}</span>
        {account.totp_required && !account.has_totp_enabled && <small>{t("চালু করা আবশ্যক")}</small>}</td>
      <td data-label={t("অনুমতি")}><span className="admin-count">{number(account.grant_count)}</span></td>
      <td className="admin-record-actions"><Link className="button button-quiet" href={`/manage/users-access/${account.id}/`} aria-label={`${t("অ্যাকাউন্ট খুলুন")}: ${account.full_name || account.email}`}><Icon name="edit" />{t("পরিচালনা করুন")}</Link></td>
    </tr>)}</tbody>
  </table></div>;
}
