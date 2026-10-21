"use client";

import Link from "next/link";
import { BrandLogo } from "./brand-logo";
import { AccountMenu } from "./account-menu";
import { AdminLanguageSwitch, useAdminLanguage } from "./admin-language";
import type { WorkspaceSession } from "@/api/types";
import { WorkspaceViewSwitch } from "./workspace-view-switch";

export function AdminHeader({ session }: { session: WorkspaceSession }) {
  const { t } = useAdminLanguage();
  return <header className="admin-topbar"><Link className="admin-brand" aria-label="বাংলা পাঠাগার" href="/manage/"><BrandLogo /><span className="admin-workspace-label">{t("পরিচালনা")}</span></Link>
    <div className="admin-topbar-actions"><WorkspaceViewSwitch session={session} target="reader" /><AdminLanguageSwitch /><AccountMenu initial={session} /></div>
  </header>;
}
