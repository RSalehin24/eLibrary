import Link from "next/link";
import { SiteNav, SiteText } from "./site-language";
import { Icon, type IconName } from "./icon";

const entries: readonly { path: string; label: string; icon: IconName }[] = [
  { path: "/catalog/", label: "প্রকাশিত বই", icon: "books" },
  { path: "/contributors/", label: "লেখক ও সহযোগী", icon: "people" },
  { path: "/categories/", label: "বইয়ের বিভাগ", icon: "tags" },
  { path: "/series/", label: "বইয়ের সিরিজ", icon: "books" },
  { path: "/collections/", label: "নির্বাচিত সংগ্রহ", icon: "read" },
];

export function CatalogBrowseNav({ current }: { current: string }) {
  return <SiteNav className="catalog-browse-navigation" aria-label="পাঠাগারে বই খুঁজুন">{entries.map(entry => <Link key={entry.path} href={entry.path} aria-current={entry.path === current ? "page" : undefined}>
    <Icon name={entry.icon} /><SiteText>{entry.label}</SiteText>
  </Link>)}</SiteNav>;
}
