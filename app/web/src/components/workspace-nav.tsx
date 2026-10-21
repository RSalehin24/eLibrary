"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { useAdminLanguage } from "./admin-language";
import { SiteText } from "./site-language";
import { Icon, type IconName } from "./icon";
import { setWorkspaceView, type WorkspaceView } from "@/lib/workspace-view";
import { navigationIsCurrent } from "@/lib/navigation-current";

const icons: Record<string, IconName> = { "/manage/": "overview", "/manage/sources/": "source", "/manage/books/": "books", "/manage/entities/": "tags", "/manage/jobs/": "jobs", "/manage/automations/": "schedule", "/manage/users-access/": "people", "/my-books/": "read", "/notes/": "notes", "/kindle/": "send", "/manage/unfinished/": "read", "/profile/": "people", "/catalog/": "search" };

type NavigationEntry = Readonly<{ href: string; label: string; workspaceView?: WorkspaceView }>;

export function WorkspaceNav({ entries, label, accountId }: { entries: readonly NavigationEntry[]; label: string; accountId?: string | number }) {
  const pathname = usePathname();
  const { t, language } = useAdminLanguage();
  const navigation = useRef<HTMLElement>(null);
  useEffect(() => {
    const container = navigation.current;
    if (!container) return;
    const current = container.querySelector<HTMLElement>('[aria-current="page"]');
    const alignCurrent = () => {
      if (current && container.scrollWidth > container.clientWidth) container.scrollLeft = current.offsetLeft - container.offsetLeft - (container.clientWidth - current.offsetWidth) / 2;
    };
    alignCurrent(); const observer = new ResizeObserver(alignCurrent); observer.observe(container);
    if (current) observer.observe(current);
    return () => observer.disconnect();
  }, [language, pathname]);
  return <nav ref={navigation} className="workspace-nav" aria-label={t(label)}>
    {entries.map((entry) => {
      const content = <>{icons[entry.href] && <Icon name={icons[entry.href]} />}<span><SiteText>{entry.label}</SiteText></span></>;
      const current = navigationIsCurrent(pathname, entry.href) ? "page" : undefined;
      return entry.workspaceView && accountId
        ? <a key={entry.href} href={entry.href} onClick={() => setWorkspaceView(accountId, entry.workspaceView!)} aria-current={current}>{content}</a>
        : <Link key={entry.href} href={entry.href} aria-current={current}>{content}</Link>;
    })}
  </nav>;
}
