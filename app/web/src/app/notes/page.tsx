import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import { PersonalNotes } from "@/components/personal-notes";
import { requireReader } from "@/lib/workspace-session";
import "../workspace.css";

export async function generateMetadata() { return localizeMetadata({ title: "আমার নোট", robots: { index: false, follow: false } }); }

export default async function NotesPage() {
  await requireReader("/notes/");
  return <section className="reader-page notes-page"><header className="page-title"><h1><SiteText>আমার নোট</SiteText></h1></header><PersonalNotes /></section>;
}
