"use client";

import Link from "next/link";
import { paginationItems, paginationURL } from "@/lib/pagination";
import { useSiteLanguage } from "./site-language";
import { Icon } from "./icon";

type PaginationProps = { page: number; totalPages?: number; hasNext?: boolean; pathname?: string; query?: string; label: string; onPageChange?: (page: number) => void; busy?: boolean };

export function NumberedPagination(props: PaginationProps) {
  const { t, number } = useSiteLanguage();
  const { page, totalPages, hasNext, label, onPageChange, busy } = props;
  const knownPages = totalPages ?? page + (hasNext ? 1 : 0);
  if (knownPages <= 1 && page === 1) return null;
  function control(target: number, text: string, className: string) {
    const children = text === "previous" ? <><span className="pagination-previous-icon"><Icon name="arrow" /></span>{t("আগের পাতা")}</>
      : text === "next" ? <>{t("পরের পাতা")}<Icon name="arrow" /></> : number(target);
    const name = text === "previous" ? t("আগের পাতা") : text === "next" ? t("পরের পাতা") : `${t("পাতা")} ${number(target)}`;
    const unavailable = target < 1 || target > knownPages;
    if (unavailable) return <span className={`button button-quiet ${className}`} aria-disabled="true">{children}</span>;
    if (onPageChange) return <button className={`button button-quiet ${className}`} type="button" aria-label={name} disabled={busy} onClick={() => onPageChange(target)}>{children}</button>;
    return <Link className={`button button-quiet ${className}`} aria-label={name} href={paginationURL(target, props)}>{children}</Link>;
  }
  return <nav className="pagination numbered-pagination" aria-label={t(label)}>
    <div className="pagination-navigation">{control(page - 1, "previous", "pagination-previous")}
      {[7, 5].map(slots => <div className="pagination-pages" data-size={slots === 7 ? "full" : "compact"} key={slots}>
        {paginationItems(page, knownPages, slots).map(item => typeof item === "number"
          ? item === page ? <span className="button pagination-current" aria-current="page" aria-label={`${t("পাতা")} ${number(page)}`} key={item}>{number(item)}</span>
            : <span key={item}>{control(item, String(item), "pagination-number")}</span>
          : <span className="pagination-gap" key={item} aria-hidden="true">…</span>)}
      </div>)}{control(page + 1, "next", "pagination-next")}</div>
    <p className="pagination-summary" aria-live="polite">{t("পাতা")} {number(page)}{totalPages !== undefined && <> / {number(totalPages)}</>}</p>
  </nav>;
}
