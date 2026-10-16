import { AdminNumber, AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import type { ManagedBooks } from "@/api/types";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "বই পরিচালনা" };
const stateLabels: Record<string, string> = { draft: "খসড়া", processing: "প্রক্রিয়াধীন", needs_review: "পর্যালোচনা প্রয়োজন",
  ready: "প্রস্তুত", published: "প্রকাশিত", archived: "সংরক্ষিত", soft_deleted: "অপসারিত" };

export default async function ManagedBooksPage({ searchParams }: { searchParams: Promise<{ page?: string }> }) {
  const session = await requireManagement("books");
  const page = Number((await searchParams).page ?? "1");
  if (!Number.isInteger(page) || page < 1) notFound();
  const books = await sessionRequest<ManagedBooks>(`manage/books/?page=${page}`);
  return <><h1><AdminText>{"বই পরিচালনা"}</AdminText></h1>
    <div className="account-actions">{session.workspaces.can_create_books && <Link className="button" href="/manage/books/new/"><AdminText>{"বইয়ের নথি তৈরি করুন"}</AdminText></Link>}
      {session.workspaces.management_sections.includes("sources") && <Link className="button button-quiet" href="/manage/sources/"><AdminText>{"উৎস থেকে বই আনুন"}</AdminText></Link>}</div>
    <p className="muted"><AdminText>{"মোট "}</AdminText><AdminNumber value={books.pagination.total_count} /><AdminText>{"টি বই"}</AdminText></p>
    <ul className="management-list">{books.entries.map((book) => <li key={book.id}>
      <div><h2><Link className="text-link" href={`/manage/books/${encodeURIComponent(book.slug)}/`}>{book.title}</Link></h2><p className="muted">{book.catalog_code} · {book.edition || "সংস্করণ উল্লেখ নেই"}</p></div>
      <span className="status-label"><AdminText>{stateLabels[book.state]}</AdminText></span></li>)}</ul>
    {!books.entries.length && <p className="empty-state"><AdminText>{"আপনার পরিচালনার তালিকায় কোনো বই নেই।"}</AdminText></p>}
    <nav className="pagination" aria-label="পরিচালনার তালিকার পাতা">
      {page > 1 && <Link className="button button-quiet" href={`?page=${page - 1}`}><AdminText>{"আগের পাতা"}</AdminText></Link>}
      <span><AdminText>{"পাতা "}</AdminText><AdminNumber value={page} /></span>
      {page * books.pagination.limit < books.pagination.total_count && <Link className="button" href={`?page=${page + 1}`}><AdminText>{"পরের পাতা"}</AdminText></Link>}
    </nav></>;
}
