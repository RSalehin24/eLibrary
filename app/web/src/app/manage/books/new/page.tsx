import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import { notFound } from "next/navigation";
import { BookCreateForm } from "@/components/book-create-form";
import { requireManagement } from "@/lib/workspace-session";
import { queryValue, type RouteQuery } from "@/lib/route-query";

export async function generateMetadata() { return localizeMetadata({ title: "বইয়ের নথি তৈরি" }); }

export default async function NewCatalogBookPage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  const session = await requireManagement("books", "/manage/books/new/");
  if (!session.workspaces.can_create_books) notFound();
  const recordType = queryValue(await searchParams, "record_type") === "manual" ? "manual" : "digital";
  return <><h1><AdminText>{"বইয়ের নথি তৈরি করুন"}</AdminText></h1><p className="muted"><AdminText>{"ডিজিটাল বইয়ের নথি তৈরির পরে EPUB আপলোড করতে পারবেন। নতুন নথি পর্যালোচনার জন্য সংরক্ষিত হবে। পাঠকের মালিকানা ও পড়ার অনুমতি আলাদাভাবে পরিচালনা করা হয়।"}</AdminText></p><BookCreateForm initialRecordType={recordType} /></>;
}
