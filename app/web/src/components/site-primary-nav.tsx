"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { SiteNav, SiteText } from "./site-language";
import { Icon, type IconName } from "./icon";

const entries = [
  { href: "/catalog/", label: "বই খুঁজুন" },
  { href: "/my-books/", label: "আমার বই" },
  { href: "/help/", label: "সহায়তা" },
];

const icons: Record<string, IconName> = { "/catalog/": "search", "/my-books/": "read", "/help/": "help", "/manage/books/": "books" };

export function SitePrimaryNav({ canManageBooks = false }: { canManageBooks?: boolean }) {
  const pathname = usePathname();
  const navigation = canManageBooks ? [{ href: "/manage/books/", label: "সব বই" }, ...entries] : entries;
  return <SiteNav aria-label="প্রধান নেভিগেশন">{navigation.map((entry) => <Link key={entry.href} href={entry.href} aria-current={pathname.startsWith(entry.href) ? "page" : undefined}><Icon name={icons[entry.href]} /><SiteText>{entry.label}</SiteText></Link>)}</SiteNav>;
}
