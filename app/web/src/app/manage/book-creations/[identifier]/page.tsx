import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { ManagedBookDetail } from "@/api/types";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "নতুন বইয়ের নথির অবস্থা" }); }

export default async function BookCreationStatusPage({ params }: { params: Promise<{ identifier: string }> }) {
  const session = await requireManagement("books"), { identifier } = await params;
  if (!session.workspaces.can_create_books || !/^[0-9a-f-]{36}$/i.test(identifier)) notFound();
  let book: ManagedBookDetail;
  try { book = await sessionRequest<ManagedBookDetail>(`manage/book-creations/${identifier}/`); }
  catch (error) { if (error instanceof APIError && [403, 404].includes(error.status)) notFound(); throw error; }
  return <><h1><AdminText>{"বইয়ের নথি তৈরি হয়েছে"}</AdminText></h1><p>{book.title}</p>
    <Link className="button" href={`/manage/books/${encodeURIComponent(book.slug)}/`}><AdminText>{"বইয়ের তথ্য সম্পাদনা করুন"}</AdminText></Link></>;
}
