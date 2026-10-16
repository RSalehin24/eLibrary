import type { PublicBookDetail } from "@/api/types";
import Link from "next/link";
import type { EntityKind } from "@/lib/catalog-entity";

type BookInformationProps = { book: PublicBookDetail; children?: React.ReactNode; entityPath?: (kind: EntityKind, slug: string) => string };

function EntityName({ name, href }: { name: string; href?: string }) {
  return href ? <Link className="text-link" href={href}>{name}</Link> : <span>{name}</span>;
}

export function BookInformation({ book, children, entityPath }: BookInformationProps) {
  const authors = book.contributors.filter((person) => person.role === "author");
  return <article className="book-detail"><div className="book-cover" aria-hidden="true"><span>{book.title}</span></div>
    <div><p className="eyebrow">{book.categories.map((category) => category.name).join(" · ") || "বইয়ের পরিচিতি"}</p><h1>{book.title}</h1>
      {authors.map((author) => <p key={author.id} className="muted"><EntityName name={author.name} href={entityPath?.("contributors", author.slug)} /></p>)}
      <dl className="book-facts"><div><dt>বইয়ের ভাষা</dt><dd>{book.language === "bn" ? "বাংলা" : book.language || "তথ্য যোগ করা হয়নি"}</dd></div>
        {book.edition && <div><dt>সংস্করণ</dt><dd>{book.edition}</dd></div>}
        <div><dt>ক্যাটালগ নম্বর</dt><dd>{book.catalog_code}</dd></div>
        {book.record_type === "manual" && <><div><dt>বইয়ের ধরন</dt><dd>কাগজের বই</dd></div><div><dt>প্রকাশক</dt><dd>{book.manual_publisher || "তথ্য যোগ করা হয়নি"}</dd></div><div><dt>বাঁধাই</dt><dd>{book.manual_binding === "hard_cover" ? "শক্ত মলাট" : book.manual_binding === "paper_back" ? "পেপারব্যাক" : "তথ্য যোগ করা হয়নি"}</dd></div>{book.manual_price !== null && <div><dt>মূল্য</dt><dd>৳ {book.manual_price}</dd></div>}<div><dt>সংকলন</dt><dd>{book.manual_is_compilation ? "হ্যাঁ" : "না"}</dd></div></>}
        {!!book.categories.length && <div><dt>বিভাগ</dt><dd>{book.categories.map((category) => <EntityName key={category.id} name={category.name} href={entityPath?.("categories", category.slug)} />)}</dd></div>}
        {!!book.series.length && <div><dt>সিরিজ</dt><dd>{book.series.map((series) => <EntityName key={series.id} name={series.name} href={entityPath?.("series", series.slug)} />)}</dd></div>}</dl>
      {(book.editorial_description || book.summary) && <section><h2>বইটি সম্পর্কে</h2><p className="book-description">{book.editorial_description || book.summary}</p></section>}
      {children}
    </div></article>;
}
