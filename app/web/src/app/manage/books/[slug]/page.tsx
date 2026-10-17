import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedBookDetail } from "@/api/types";
import { BookEditorialForm } from "@/components/book-editorial-form";
import { routeSlug } from "@/lib/route-slug";
import { requireManagement } from "@/lib/workspace-session";
import { ReaderBookCover } from "@/components/reader-book-cover";

export async function generateMetadata() { return localizeMetadata({ title: "বই সম্পাদনা" }); }

export default async function ManagedBookPage({ params }: { params: Promise<{ slug: string }> }) {
  const slug = routeSlug((await params).slug);
  const session = await requireManagement("books", `/manage/books/${encodeURIComponent(slug)}/`);
  let book: ManagedBookDetail;
  try { book = await sessionRequest<ManagedBookDetail>(`manage/books/${encodeURIComponent(slug)}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href="/manage/books/"><AdminText>{"← বই পরিচালনায় ফিরুন"}</AdminText></Link>
    <div className="source-book-overview"><ReaderBookCover slug={book.slug} title={book.title} /><h1>{book.title}</h1></div><BookEditorialForm key={book.id} initialBook={book} canProcess={session.workspaces.management_sections.includes("jobs")} />
    {session.workspaces.can_create_books && <Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(book.slug)}/relationships/`}><AdminText>{"বইয়ের সম্পর্ক ও সংস্করণ সম্পাদনা করুন"}</AdminText></Link>}
    </>;
}
