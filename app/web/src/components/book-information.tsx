import { SiteText } from "@/components/site-language";
import type { PublicBookDetail } from "@/api/types";
import Link from "next/link";
import type { EntityKind } from "@/lib/catalog-entity";
import { BookCover } from "./book-cover";

type BookInformationProps = { book: PublicBookDetail; children?: React.ReactNode; entityPath?: (kind: EntityKind, slug: string) => string };

function EntityName({ name, href }: { name: string; href?: string }) {
  return href ? <Link className="text-link" href={href}>{name}</Link> : <span>{name}</span>;
}

export function BookInformation({ book, children, entityPath }: BookInformationProps) {
  const authors = book.contributors.filter((person) => person.role === "author");
  return <article className="book-detail"><BookCover title={book.title} author={authors.map((author) => author.name).join(", ")} coverUrl={book.cover_url} />
    <div className="book-detail-copy"><p className="eyebrow">{book.categories.map((category) => category.name).join(" · ") || <SiteText>{"বইয়ের পরিচিতি"}</SiteText>}</p><h1>{book.title}</h1>
      {authors.map((author) => <p key={author.id} className="muted"><EntityName name={author.name} href={entityPath?.("contributors", author.slug)} /></p>)}
    </div><div className="book-primary-actions">{children}</div>
    <div className="book-detail-body"><dl className="book-facts"><div><dt><SiteText>{"বইয়ের ভাষা"}</SiteText></dt><dd>{book.language === "bn" ? <SiteText>{"বাংলা"}</SiteText> : book.language || <SiteText>{"তথ্য যোগ করা হয়নি"}</SiteText>}</dd></div>
        {book.edition && <div><dt><SiteText>{"সংস্করণ"}</SiteText></dt><dd>{book.edition}</dd></div>}
        <div><dt><SiteText>{"ক্যাটালগ নম্বর"}</SiteText></dt><dd>{book.catalog_code}</dd></div>
        {book.record_type === "manual" && <><div><dt><SiteText>{"বইয়ের ধরন"}</SiteText></dt><dd><SiteText>{"কাগজের বই"}</SiteText></dd></div><div><dt><SiteText>{"প্রকাশক"}</SiteText></dt><dd>{book.manual_publisher || <SiteText>{"তথ্য যোগ করা হয়নি"}</SiteText>}</dd></div><div><dt><SiteText>{"বাঁধাই"}</SiteText></dt><dd>{book.manual_binding === "hard_cover" ? <SiteText>{"শক্ত মলাট"}</SiteText> : book.manual_binding === "paper_back" ? <SiteText>{"পেপারব্যাক"}</SiteText> : <SiteText>{"তথ্য যোগ করা হয়নি"}</SiteText>}</dd></div>{book.manual_price !== null && <div><dt><SiteText>{"মূল্য"}</SiteText></dt><dd><SiteText>{"৳ "}</SiteText>{book.manual_price}</dd></div>}<div><dt><SiteText>{"সংকলন"}</SiteText></dt><dd>{book.manual_is_compilation ? <SiteText>{"হ্যাঁ"}</SiteText> : <SiteText>{"না"}</SiteText>}</dd></div></>}
        {!!book.categories.length && <div><dt><SiteText>{"বিভাগ"}</SiteText></dt><dd>{book.categories.map((category) => <EntityName key={category.id} name={category.name} href={entityPath?.("categories", category.slug)} />)}</dd></div>}
        {!!book.series.length && <div><dt><SiteText>{"সিরিজ"}</SiteText></dt><dd>{book.series.map((series) => <EntityName key={series.id} name={series.name} href={entityPath?.("series", series.slug)} />)}</dd></div>}</dl>
      {(book.editorial_description || book.summary) && <section><h2><SiteText>{"বইটি সম্পর্কে"}</SiteText></h2><p className="book-description">{book.editorial_description || book.summary}</p></section>}
    </div></article>;
}
