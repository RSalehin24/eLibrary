"use client";

import Link from "next/link";
import { useState } from "react";
import type { PublicBook } from "@/api/types";
import { catalogEntityPath } from "@/lib/catalog-entity-path";
import { BookCard } from "./book-card";
import { Icon } from "./icon";
import { SiteNumber, SiteText, useSiteLanguage } from "./site-language";

type BrowseBook = PublicBook & { progress_percent?: number | null };

export function BookResults({ books, library = false, busy = false }: { books: BrowseBook[]; library?: boolean; busy?: boolean }) {
  const [layout, setLayout] = useState("cards"), { t } = useSiteLanguage();
  const path = (book: PublicBook) => `/${library ? "my-books" : "books"}/${encodeURIComponent(book.slug)}/`;
  return <section className="book-results" aria-busy={busy}>
    <div className="book-layout-controls" role="group" aria-label={t("তালিকার ধরন")}>
      <button className="button button-quiet" aria-pressed={layout === "cards"} onClick={() => setLayout("cards")}><Icon name="overview" /><SiteText>কার্ড</SiteText></button>
      <button className="button button-quiet" aria-pressed={layout === "table"} onClick={() => setLayout("table")}><Icon name="jobs" /><SiteText>ছক</SiteText></button>
    </div>
    {layout === "cards" ? <div className="book-grid">{books.map(book => <div key={book.id}><BookCard book={book} href={path(book)} />
      {book.progress_percent != null && <p className="muted"><SiteText>পড়া হয়েছে </SiteText><SiteNumber value={book.progress_percent} />%</p>}
    </div>)}</div> : <div className="book-table-scroll" role="region" tabIndex={0} aria-label={t("বইয়ের তালিকা")}><table className="book-results-table">
      <caption className="visually-hidden"><SiteText>বইয়ের তালিকা</SiteText></caption>
      <thead><tr>{["বইয়ের নাম", "লেখক", "বিভাগ", "সিরিজ", "ক্যাটালগ নম্বর"].map(label => <th key={label} scope="col"><SiteText>{label}</SiteText></th>)}</tr></thead>
      <tbody>{books.map(book => <tr key={book.id}>
        <th scope="row"><Link href={path(book)}>{book.title}</Link>{book.edition && <small>{book.edition}</small>}</th>
        <td>{book.contributors.filter(person => person.role === "author").map(person => <Link key={person.id} href={`${catalogEntityPath("contributors", person.slug)}?role=author`}>{person.name}</Link>)}</td>
        <td>{book.categories.map(category => <Link key={category.id} href={catalogEntityPath("categories", category.slug)}>{category.name}</Link>)}</td>
        <td>{book.series.map(series => <Link key={series.id} href={catalogEntityPath("series", series.slug)}>{series.name}</Link>)}</td>
        <td>{book.catalog_code || "—"}</td>
      </tr>)}</tbody>
    </table></div>}
  </section>;
}
