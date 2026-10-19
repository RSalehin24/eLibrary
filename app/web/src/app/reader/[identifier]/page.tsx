import { localizeMetadata } from "@/lib/metadata-language";
import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { Bookmark, Highlight, ReaderSession } from "@/api/types";
import { BookReader } from "@/components/book-reader";
import { requireReader } from "@/lib/workspace-session";
import { queryValue, type RouteQuery } from "@/lib/route-query";
import { annotationPosition } from "@/lib/annotation-position";
import type { ReadingPosition } from "@/lib/reading-position";

async function requestedPosition(identifier: string, parameters: RouteQuery, session: ReaderSession) {
  const bookmark = queryValue(parameters, "bookmark"), highlight = queryValue(parameters, "highlight");
  if (!bookmark && !highlight) return;
  if (bookmark && highlight || !/^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$/i.test(bookmark || highlight)) notFound();
  const kind = bookmark ? "bookmarks" : "highlights";
  const annotation = await sessionRequest<Bookmark | Highlight>(`reading/sessions/${identifier}/${kind}/${bookmark || highlight}/`);
  return annotationPosition(annotation, session);
}

export async function generateMetadata() { return localizeMetadata({ title: "বই পড়ুন", robots: { index: false, follow: false } }); }

export default async function ReaderPage({ params, searchParams }: { params: Promise<{ identifier: string }>; searchParams: Promise<RouteQuery> }) {
  const { identifier } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(identifier)) notFound();
  await requireReader(`/reader/${identifier}/`);
  let session: ReaderSession;
  let position: ReadingPosition | undefined;
  try {
    session = await sessionRequest<ReaderSession>(`reading/sessions/${identifier}/`);
    position = await requestedPosition(identifier, await searchParams, session);
  }
  catch (error) { if (error instanceof APIError && [403, 404, 409].includes(error.status)) notFound(); throw error; }
  return <BookReader key={session.id} session={session} initialPosition={position} />;
}
