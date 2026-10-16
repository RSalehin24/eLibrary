import Link from "next/link";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { PublicBookDetail } from "@/api/types";
import type { PhysicalReadingLog } from "@/api/types";
import { PhysicalReadingForm } from "@/components/physical-reading-form";
import { SaveBookButton } from "@/components/save-book-button";
import { BookInformation } from "@/components/book-information";
import { BookActions } from "@/components/book-actions";
import { requireReader } from "@/lib/workspace-session";
import { routeSlug } from "@/lib/route-slug";

export const metadata = { title: "আমার বইয়ের পরিচিতি" };

export default async function PrivateBookPage({ params }: { params: Promise<{ slug: string }> }) {
  const slug = routeSlug((await params).slug);
  await requireReader(`/my-books/${encodeURIComponent(slug)}/`);
  let book: PublicBookDetail;
  try { book = await sessionRequest<PublicBookDetail>(`me/books/${encodeURIComponent(slug)}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href="/my-books/">← আমার বইয়ে ফিরুন</Link>
    <BookInformation book={book}><BookActions slug={book.slug} recordType={book.record_type} /><SaveBookButton slug={book.slug} /></BookInformation>
    {book.record_type === "manual" && <PhysicalReadingForm slug={book.slug} initialLog={await sessionRequest<PhysicalReadingLog>(`me/books/${encodeURIComponent(book.slug)}/physical-log/`)} />}</>;
}
