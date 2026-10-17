"use client";

import Link from "next/link";
import { BrandMark } from "./brand-mark";
import { AccountMenu } from "./account-menu";
import { AdminLanguageSwitch, useAdminLanguage } from "./admin-language";
import type { WorkspaceSession } from "@/api/types";

export function AdminHeader({ session }: { session: WorkspaceSession }) {
  const { t } = useAdminLanguage();
  return <header className="admin-topbar"><Link className="admin-brand" aria-label={t("বাংলা পাঠাগার")} href="/manage/"><BrandMark size={32} /><span>{t("বাংলা পাঠাগার")}<small>{t("পরিচালনা")}</small></span></Link>
    <div className="admin-topbar-actions"><AdminLanguageSwitch /><AccountMenu initial={session} /></div>
  </header>;
}
