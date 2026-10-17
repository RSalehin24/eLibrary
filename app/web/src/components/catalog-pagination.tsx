import { SiteNav, SiteText, SiteNumber } from "@/components/site-language";
import Link from "next/link";

type PaginationProps = { pathname: string; page: number; hasMore: boolean; query?: string; filters?: Readonly<Record<string, string>> };

export function CatalogPagination({ pathname, page, hasMore, query, filters }: PaginationProps) {
  const pageLink = (number: number) => `${pathname}?${new URLSearchParams({ ...filters, ...(query ? { q: query } : {}), page: String(number) })}`;
  return <SiteNav className="pagination" aria-label="বইয়ের তালিকার পাতা">
    {page > 1 && <Link className="button button-quiet" href={pageLink(page - 1)}><SiteText>{"আগের পাতা"}</SiteText></Link>}
    <span><SiteText>{"পাতা "}</SiteText><SiteNumber value={page} /></span>
    {hasMore && <Link className="button button-quiet" href={pageLink(page + 1)}><SiteText>{"পরের পাতা"}</SiteText></Link>}
  </SiteNav>;
}
