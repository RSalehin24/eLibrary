import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { PublicBookDetail } from "@/api/types";
import type { PhysicalReadingLog } from "@/api/types";
import { PhysicalReadingForm } from "@/components/physical-reading-form";
import { BookInformation } from "@/components/book-information";
import { BookActions } from "@/components/book-actions";
import { requireReader } from "@/lib/workspace-session";
import { routeSlug } from "@/lib/route-slug";
import { BookReadingSummary } from "@/components/book-reading-summary";

export async function generateMetadata() { return localizeMetadata({ title: "আমার বইয়ের পরিচিতি" }); }

export default async function PrivateBookPage({ params }: { params: Promise<{ slug: string }> }) {
  const slug = routeSlug((await params).slug);
  await requireReader(`/my-books/${encodeURIComponent(slug)}/`);
  let book: PublicBookDetail;
  try { book = await sessionRequest<PublicBookDetail>(`me/books/${encodeURIComponent(slug)}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href="/my-books/"><SiteText>{"← আমার বইয়ে ফিরুন"}</SiteText></Link>
    <BookInformation book={book} personal><BookActions slug={book.slug} recordType={book.record_type} /></BookInformation>
    {book.record_type !== "manual" && <BookReadingSummary slug={book.slug} />}
    {book.record_type === "manual" && <PhysicalReadingForm slug={book.slug} initialLog={await sessionRequest<PhysicalReadingLog>(`me/books/${encodeURIComponent(book.slug)}/physical-log/`)} />}</>;
}
