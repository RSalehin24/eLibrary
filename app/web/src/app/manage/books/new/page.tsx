import { AdminText } from "@/components/admin-language";
import { notFound } from "next/navigation";
import { BookCreateForm } from "@/components/book-create-form";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "বইয়ের নথি তৈরি" };

export default async function NewCatalogBookPage() {
  const session = await requireManagement("books", "/manage/books/new/");
  if (!session.workspaces.can_create_books) notFound();
  return <><h1><AdminText>{"বইয়ের নথি তৈরি করুন"}</AdminText></h1><p className="muted"><AdminText>{"ডিজিটাল বইয়ের নথি তৈরির পরে EPUB আপলোড করতে পারবেন। নতুন নথি পর্যালোচনার জন্য সংরক্ষিত হবে। পাঠকের মালিকানা ও পড়ার অনুমতি আলাদাভাবে পরিচালনা করা হয়।"}</AdminText></p><BookCreateForm /></>;
}
