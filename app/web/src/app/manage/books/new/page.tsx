import { localizeMetadata } from "@/lib/metadata-language";
import { AdminText } from "@/components/admin-language";
import { notFound } from "next/navigation";
import { BookCreateForm } from "@/components/book-create-form";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "বইয়ের নথি তৈরি" }); }

export default async function NewCatalogBookPage() {
  const session = await requireManagement("books", "/manage/books/new/");
  if (!session.workspaces.can_create_books) notFound();
  return <><h1><AdminText>{"বইয়ের নথি তৈরি করুন"}</AdminText></h1><p className="muted"><AdminText>{"বইয়ের নথি তৈরি করে EPUB আপলোড করুন। প্রস্তুতি সফল হলে বইটি স্বয়ংক্রিয়ভাবে প্রকাশিত হবে।"}</AdminText></p><BookCreateForm canEdit={session.workspaces.can_edit_books} /></>;
}
