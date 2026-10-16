import Link from "next/link";
import { publicRequest } from "@/api/server";
import type { BookCollection } from "@/api/types";

export async function RelatedEditions({ slug }: { slug: string }) {
  const editions = await publicRequest<BookCollection>(`catalog/books/${encodeURIComponent(slug)}/editions/?limit=8`);
  if (!editions.entries.length) return null;
  return <section><h2>এই কাজের অন্য সংস্করণ</h2><ul className="management-list">{editions.entries.map((book) => <li key={book.id}><Link className="text-link" href={`/books/${encodeURIComponent(book.slug)}/`}>{book.title}{book.edition ? ` · ${book.edition}` : ""}{book.language ? ` · ${book.language}` : ""}</Link></li>)}</ul>
    {editions.has_more && <Link className="text-link" href={`/books/${encodeURIComponent(slug)}/editions/`}>সব সংস্করণ দেখুন →</Link>}
  </section>;
}
