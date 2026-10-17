import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { notFound } from "next/navigation";
import { APIError } from "@/api/http";
import { sessionRequest } from "@/api/server";
import type { BookRelationships } from "@/api/types";
import { BookRelationshipsForm } from "@/components/book-relationships-form";
import { routeSlug } from "@/lib/route-slug";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "বইয়ের সম্পর্ক ও সংস্করণ" }); }

export default async function BookRelationshipsPage({ params }: { params: Promise<{ slug: string }> }) {
  const slug = routeSlug((await params).slug);
  const session = await requireManagement("books", `/manage/books/${encodeURIComponent(slug)}/relationships/`);
  if (!session.workspaces.can_create_books) notFound();
  let relationships: BookRelationships;
  try { relationships = await sessionRequest<BookRelationships>(`manage/books/${encodeURIComponent(slug)}/relationships/`); }
  catch (error) { if (error instanceof APIError && error.status === 404) notFound(); throw error; }
  return <><Link className="text-link" href={`/manage/books/${encodeURIComponent(slug)}/`}><AdminText>{"← বই সম্পাদনায় ফিরুন"}</AdminText></Link>
    <h1><AdminText>{"বইয়ের সম্পর্ক ও সংস্করণ"}</AdminText></h1><BookRelationshipsForm key={relationships.id} slug={slug} initialRelationships={relationships} /></>;
}
