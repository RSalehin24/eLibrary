import Link from "next/link";
import { bengaliNumber } from "@/lib/site";

type PaginationProps = { pathname: string; page: number; hasMore: boolean; query?: string };

export function CatalogPagination({ pathname, page, hasMore, query }: PaginationProps) {
  const pageLink = (number: number) => `${pathname}?${new URLSearchParams({ ...(query ? { q: query } : {}), page: String(number) })}`;
  return <nav className="pagination" aria-label="বইয়ের তালিকার পাতা">
    {page > 1 && <Link className="button button-quiet" href={pageLink(page - 1)}>আগের পাতা</Link>}
    <span>পাতা {bengaliNumber(page)}</span>
    {hasMore && <Link className="button button-quiet" href={pageLink(page + 1)}>পরের পাতা</Link>}
  </nav>;
}
