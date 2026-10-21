import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { PersonalBookDetail } from "@/api/types";
import type { PhysicalReadingLog } from "@/api/types";
import { PhysicalReadingForm } from "@/components/physical-reading-form";
import { BookInformation } from "@/components/book-information";
import { BookActions } from "@/components/book-actions";
import { requireReader } from "@/lib/workspace-session";
import { routeSlug } from "@/lib/route-slug";
import { BookReadingSummary } from "@/components/book-reading-summary";
import { queryValue, type RouteQuery } from "@/lib/route-query";
import { isPersonalLibraryView } from "@/lib/book-detail-links";

export async function generateMetadata() { return localizeMetadata({ title: "আমার বইয়ের পরিচিতি" }); }

export default async function PrivateBookPage({ params, searchParams }: { params: Promise<{ slug: string }>; searchParams: Promise<RouteQuery> }) {
  const slug = routeSlug((await params).slug);
  await requireReader(`/my-books/${encodeURIComponent(slug)}/`);
  const requestedView = queryValue(await searchParams, "view");
  if (requestedView && !isPersonalLibraryView(requestedView)) notFound();
  let book: PersonalBookDetail;
  try { book = await sessionRequest<PersonalBookDetail>(`me/books/${encodeURIComponent(slug)}/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  const view = requestedView || book.library_view;
  const returnPath = view === "all" ? "/my-books/" : `/my-books/?${new URLSearchParams({ view })}`;
  return <><Link className="text-link" href={returnPath}><SiteText>{"← আমার বইয়ে ফিরুন"}</SiteText></Link>
    <BookInformation book={book} personal personalView={view}><BookActions slug={book.slug} recordType={book.record_type} /></BookInformation>
    {book.record_type !== "manual" && <BookReadingSummary slug={book.slug} />}
    {book.record_type === "manual" && <PhysicalReadingForm slug={book.slug} initialLog={await sessionRequest<PhysicalReadingLog>(`me/books/${encodeURIComponent(book.slug)}/physical-log/`)} />}</>;
}
