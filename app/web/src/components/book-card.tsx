import Link from "next/link";
import type { PublicBook } from "@/api/types";

export function BookCard({ book, href = `/books/${encodeURIComponent(book.slug)}/` }: { book: PublicBook; href?: string }) {
  const authors = book.contributors.filter((person) => person.role === "author");
  return <article className="book-card">
    <div className="book-cover" aria-hidden="true"><span>{book.title}</span></div>
    <div className="book-card-body">
      <p className="eyebrow">{book.categories.map((category) => category.name).join(" · ") || "বই"}</p>
      <h3><Link href={href}>{book.title}</Link></h3>
      <p className="muted">{authors.map((author) => author.name).join(", ") || "লেখকের তথ্য যোগ করা হয়নি"}</p>
      {book.edition && <p className="muted">সংস্করণ: {book.edition}</p>}
      <Link className="text-link" href={href}>বইয়ের পরিচিতি <span aria-hidden="true">↗</span></Link>
    </div>
  </article>;
}
