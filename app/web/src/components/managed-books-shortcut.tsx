import Link from "next/link";
import { getWorkspaceSession, getWorkspaceView } from "@/lib/workspace-session";
import { Icon } from "./icon";
import { SiteText } from "./site-language";

export async function ManagedBooksShortcut() {
  const session = await getWorkspaceSession();
  if (!session.workspaces.management_sections.includes("books") || await getWorkspaceView() === "reader") return null;
  return <Link className="managed-books-shortcut text-link" href="/manage/books/"><Icon name="books" /><SiteText>{"সব বই দেখুন"}</SiteText></Link>;
}
