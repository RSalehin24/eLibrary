"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAdminLanguage } from "./admin-language";

type NavigationEntry = Readonly<{ href: string; label: string }>;

export function WorkspaceNav({ entries, label }: { entries: readonly NavigationEntry[]; label: string }) {
  const pathname = usePathname();
  const { t } = useAdminLanguage();
  return <nav className="workspace-nav" aria-label={t(label)}>
    {entries.map((entry) => <Link key={entry.href} href={entry.href} aria-current={pathname === entry.href || entry.href !== "/manage/" && pathname.startsWith(entry.href) ? "page" : undefined}>{t(entry.label)}</Link>)}
  </nav>;
}
