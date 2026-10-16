"use client";

import Link from "next/link";
import type { ManagedAccounts } from "@/api/types";
import { useAdminLanguage } from "./admin-language";

export function AdminPagination({ pagination, filter, label }: { pagination: ManagedAccounts["pagination"]; filter: string; label: string }) {
  const { t, number } = useAdminLanguage();
  const pageLink = (page: number) => { const parameters = new URLSearchParams(filter); parameters.set("page", String(page)); return `?${parameters}`; };
  return <nav className="pagination" aria-label={t(label)}>
    {pagination.page > 1 && <Link className="button button-quiet" href={pageLink(pagination.page - 1)}>{t("আগের পাতা")}</Link>}
    <span>{t("পাতা")} {number(pagination.page)}</span>
    {pagination.page * pagination.limit < pagination.total_count && <Link className="button" href={pageLink(pagination.page + 1)}>{t("পরের পাতা")}</Link>}
  </nav>;
}
