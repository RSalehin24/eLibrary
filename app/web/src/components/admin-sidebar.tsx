"use client";

import { useAdminLanguage } from "./admin-language";

export function AdminSidebar({ children }: { children: React.ReactNode }) {
  const { t } = useAdminLanguage();
  return <aside className="admin-sidebar" aria-label={t("অ্যাডমিন মেনু")}>{children}</aside>;
}
