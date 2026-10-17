import Link from "next/link";
import { getWorkspaceSession } from "@/lib/workspace-session";
import { Icon } from "./icon";
import { SiteText } from "./site-language";

export async function ManagedBooksShortcut() {
  const session = await getWorkspaceSession();
  if (!session.workspaces.management_sections.includes("books")) return null;
  return <aside className="catalog-management-shortcut"><div><strong><SiteText>{"আপনার তৈরি করা বই খুঁজছেন?"}</SiteText></strong>
    <p><SiteText>{"খসড়া, প্রস্তুত ও প্রকাশিত সব বই একসঙ্গে দেখুন।"}</SiteText></p></div>
    <Link className="button" href="/manage/books/"><Icon name="books" /><SiteText>{"সব বই দেখুন"}</SiteText></Link></aside>;
}
