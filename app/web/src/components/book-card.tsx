import { SiteText } from "@/components/site-language";
import Link from "next/link";
import type { PublicBook } from "@/api/types";
import { BookCover } from "./book-cover";
import { Icon } from "./icon";
import { Fragment } from "react";
import { catalogEntityPath } from "@/lib/catalog-entity-path";
import type { EntityKind } from "@/lib/catalog-entity";

type EntityLink = (kind: EntityKind, slug: string, role?: string) => string;

export function BookCard({ book, href = `/books/${encodeURIComponent(book.slug)}/`, actionLabel = "বইয়ের পরিচিতি", entityHref }: { book: PublicBook; href?: string; actionLabel?: string; entityHref?: EntityLink }) {
  const authors = book.contributors.filter((person) => person.role === "author");
  const linkedMetadata = !!entityHref || !("state" in book) || book.state === "published";
  const entityLink: EntityLink = entityHref ?? ((kind, slug, role) => `${catalogEntityPath(kind, slug)}${role ? `?role=${encodeURIComponent(role)}` : ""}`);
  return <article className="book-card">
    <BookCover title={book.title} author={authors.map((author) => author.name).join(", ")} coverUrl={book.cover_url} />
    <div className="book-card-body">
      <p className="eyebrow">{book.categories.length ? book.categories.map((category, index) => <Fragment key={category.id}>{index > 0 && " · "}{linkedMetadata ? <Link href={entityLink("categories", category.slug)}>{category.name}</Link> : category.name}</Fragment>) : <SiteText>{"বই"}</SiteText>}</p>
      <h3><Link href={href}>{book.title}</Link></h3>
      <p className="muted">{authors.length ? authors.map((author, index) => <Fragment key={author.id}>{index > 0 && " · "}{linkedMetadata ? <Link href={entityLink("contributors", author.slug, "author")}>{author.name}</Link> : author.name}</Fragment>) : <SiteText>{"লেখকের তথ্য যোগ করা হয়নি"}</SiteText>}</p>
      {book.series.length > 0 && <p className="muted">{book.series.map((series, index) => <Fragment key={series.id}>{index > 0 && " · "}{linkedMetadata ? <Link href={entityLink("series", series.slug)}>{series.name}</Link> : series.name}</Fragment>)}</p>}
      {book.edition && <p className="muted"><SiteText>{"সংস্করণ: "}</SiteText>{book.edition}</p>}
      <Link className="text-link" href={href}><Icon name="arrow" /><SiteText>{actionLabel}</SiteText></Link>
    </div>
  </article>;
}
