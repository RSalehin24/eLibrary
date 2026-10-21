import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import { notFound } from "next/navigation";
import { BookCreateForm } from "@/components/book-create-form";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "বইয়ের নথি তৈরি" }); }

export default async function NewCatalogBookPage() {
  const session = await requireManagement("books", "/manage/books/new/");
  if (!session.workspaces.can_create_books) notFound();
  return <><h1><AdminText>{"বইয়ের নথি তৈরি করুন"}</AdminText></h1><p className="muted"><AdminText>{"ডিজিটাল বইয়ের নথি তৈরির পরে EPUB আপলোড করতে পারবেন। ফাইল প্রস্তুত হলে প্রকাশ করতে পারবেন। পাঠকের মালিকানা ও পড়ার অনুমতি আলাদাভাবে পরিচালনা করা হয়।"}</AdminText></p><BookCreateForm /></>;
}
