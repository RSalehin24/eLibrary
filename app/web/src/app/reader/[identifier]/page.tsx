import { notFound } from "next/navigation";
import { sessionRequest } from "@/api/server";
import { APIError } from "@/api/http";
import type { ReaderSession } from "@/api/types";
import { BookReader } from "@/components/book-reader";
import { requireReader } from "@/lib/workspace-session";

export const metadata = { title: "বই পড়ুন", robots: { index: false, follow: false } };

export default async function ReaderPage({ params }: { params: Promise<{ identifier: string }> }) {
  const { identifier } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(identifier)) notFound();
  await requireReader(`/reader/${identifier}/`);
  let session: ReaderSession;
  try { session = await sessionRequest<ReaderSession>(`reading/sessions/${identifier}/`); }
  catch (error) { if (error instanceof APIError && [403, 404, 409].includes(error.status)) notFound(); throw error; }
  return <BookReader key={session.id} session={session} />;
}
