"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAdminLanguage } from "./admin-language";
import { Icon, type IconName } from "./icon";

const icons: Record<string, IconName> = { "/manage/": "overview", "/manage/sources/": "source", "/manage/books/": "books", "/manage/entities/": "tags", "/manage/jobs/": "jobs", "/manage/automations/": "schedule", "/manage/users-access/": "people", "/my-books/": "read", "/notes/": "notes", "/kindle/": "send", "/manage/unfinished/": "read", "/profile/": "people", "/catalog/": "search" };

type NavigationEntry = Readonly<{ href: string; label: string }>;

export function WorkspaceNav({ entries, label }: { entries: readonly NavigationEntry[]; label: string }) {
  const pathname = usePathname();
  const { t } = useAdminLanguage();
  return <nav className="workspace-nav" aria-label={t(label)}>
    {entries.map((entry) => <Link key={entry.href} href={entry.href} aria-current={pathname === entry.href || entry.href !== "/manage/" && pathname.startsWith(entry.href) ? "page" : undefined}>{icons[entry.href] && <Icon name={icons[entry.href]} />}<span>{t(entry.label)}</span></Link>)}
  </nav>;
}
