import Link from "next/link";
import { canonicalURL } from "@/lib/site";
import { StructuredData } from "./structured-data";

type Breadcrumb = { name: string; path: string };

export function Breadcrumbs({ entries }: { entries: Breadcrumb[] }) {
  return <><nav aria-label="অবস্থান">{entries.map((entry, index) => <span key={entry.path}>
    {index > 0 && <span aria-hidden="true"> / </span>}
    {index === entries.length - 1 ? <span aria-current="page">{entry.name}</span> : <Link className="text-link" href={entry.path}>{entry.name}</Link>}
  </span>)}</nav><StructuredData data={{ "@context": "https://schema.org", "@type": "BreadcrumbList",
    itemListElement: entries.map((entry, index) => ({ "@type": "ListItem", position: index + 1, name: entry.name, item: canonicalURL(entry.path) })),
  }} /></>;
}
