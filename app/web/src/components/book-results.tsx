"use client";

import Link from "next/link";
import { useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import type { PublicBook } from "@/api/types";
import { bookDetailEntityPath, isPersonalLibraryView } from "@/lib/book-detail-links";
import type { EntityKind } from "@/lib/catalog-entity";
import { BookCard } from "./book-card";
import { Icon } from "./icon";
import { SiteText, useSiteLanguage } from "./site-language";
import { BookListActions, useBookListControls } from "./book-list-actions";

type BrowseBook = PublicBook & { progress_percent?: number | null };
const tableColumns = [
  { label: "বইয়ের নাম", width: "29%" }, { label: "লেখক", width: "18%" },
  { label: "বিভাগ", width: "14%" }, { label: "সিরিজ", width: "13%" },
  { label: "ক্যাটালগ নম্বর", width: "9%" }, { label: "বইয়ের কাজ", width: "17%" },
];

export function BookResults({ books, library = false, busy = false }: { books: BrowseBook[]; library?: boolean; busy?: boolean }) {
  const [layout, setLayout] = useState("cards"), { t } = useSiteLanguage();
  const controls = useBookListControls(books.map(book => book.slug)), router = useRouter();
  const search = useSearchParams();
  const saved = library ? () => router.refresh() : undefined;
  const requestedView = search.get("view"), view = isPersonalLibraryView(requestedView) ? requestedView : "all";
  const path = (book: PublicBook) => `/${library ? "my-books" : "books"}/${encodeURIComponent(book.slug)}/${library && view !== "all" ? `?view=${view}` : ""}`;
  const entityPath = (kind: EntityKind, slug: string, role = "") => bookDetailEntityPath({ kind, slug, role, personal: library, view });
  return <section className="book-results" aria-busy={busy}>
    <div className="book-layout-controls" role="group" aria-label={t("তালিকার ধরন")}>
      <button className="button button-quiet" aria-pressed={layout === "cards"} onClick={() => setLayout("cards")}><Icon name="overview" /><SiteText>কার্ড</SiteText></button>
      <button className="button button-quiet" aria-pressed={layout === "table"} onClick={() => setLayout("table")}><Icon name="jobs" /><SiteText>ছক</SiteText></button>
    </div>
    {controls.failed && <p className="notice" role="alert"><SiteText>সংরক্ষিত তালিকার অবস্থা নিশ্চিত করা যায়নি। </SiteText><button type="button" className="button button-quiet" onClick={() => void controls.retry()}><SiteText>বর্তমান অবস্থা দেখুন</SiteText></button></p>}
    {layout === "cards" ? <div className="book-grid">{books.map(book => <BookCard key={book.id} book={book} href={path(book)} entityHref={entityPath} progress={book.progress_percent} actions={controls.available && <BookListActions control={controls.entries.get(book.slug)} onSaved={saved} />} />)}</div> : <div className="book-table-scroll" role="region" tabIndex={0} aria-label={t("বইয়ের তালিকা")}><table className="book-results-table">
      <caption className="visually-hidden"><SiteText>বইয়ের তালিকা</SiteText></caption>
      <colgroup>{tableColumns.map(column => <col key={column.label} style={{ width: column.width }} />)}</colgroup>
      <thead><tr>{tableColumns.map(column => <th key={column.label} scope="col"><SiteText>{column.label}</SiteText></th>)}</tr></thead>
      <tbody>{books.map(book => <tr key={book.id}>
        <th scope="row"><Link href={path(book)}>{book.title}</Link>{book.edition && <small>{book.edition}</small>}</th>
        <td>{book.contributors.filter(person => person.role === "author").map(person => <Link key={person.id} href={entityPath("contributors", person.slug, "author")}>{person.name}</Link>)}</td>
        <td>{book.categories.map(category => <Link key={category.id} href={entityPath("categories", category.slug)}>{category.name}</Link>)}</td>
        <td>{book.series.map(series => <Link key={series.id} href={entityPath("series", series.slug)}>{series.name}</Link>)}</td>
        <td>{book.catalog_code || "—"}</td>
        <td><div className="book-table-actions"><Link className="button button-quiet" aria-label={t("বইয়ের পরিচিতি")} title={t("বইয়ের পরিচিতি")} href={path(book)}><Icon name="read" /><SiteText>বইয়ের পরিচিতি</SiteText></Link>
          {controls.available && <BookListActions control={controls.entries.get(book.slug)} onSaved={saved} />}</div></td>
      </tr>)}</tbody>
    </table></div>}
  </section>;
}
