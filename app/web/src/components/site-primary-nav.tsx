"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SiteNav, SiteText } from "./site-language";
import { Icon, type IconName } from "./icon";
import { managementNavigation } from "@/lib/management-navigation";
import type { WorkspaceView } from "@/lib/workspace-view";
import { navigationIsCurrent } from "@/lib/navigation-current";

const entries = [
  { href: "/my-books/", label: "আমার বই" },
  { href: "/catalog/", label: "বই খুঁজুন" },
  { href: "/notes/", label: "আমার নোট" },
  { href: "/kindle/", label: "কিন্ডল" },
];
const icons: Record<string, IconName> = { "/catalog/": "search", "/my-books/": "read", "/notes/": "notes", "/kindle/": "send", "/manage/sources/": "source", "/manage/books/": "books", "/manage/entities/": "tags", "/manage/jobs/": "jobs", "/manage/automations/": "schedule", "/manage/users-access/": "people" };

export function SitePrimaryNav({ view, managementSections }: { view: WorkspaceView; managementSections: readonly string[] }) {
  const pathname = usePathname();
  const navigation = view === "admin" ? managementNavigation(managementSections) : entries;
  return <SiteNav className="primary-navigation" aria-label={view === "admin" ? "পরিচালনার নেভিগেশন" : "প্রধান নেভিগেশন"}>{navigation.map((entry) => <Link key={entry.href} href={entry.href} aria-current={navigationIsCurrent(pathname, entry.href) ? "page" : undefined}><Icon name={icons[entry.href]} /><SiteText>{entry.label}</SiteText></Link>)}</SiteNav>;
}
