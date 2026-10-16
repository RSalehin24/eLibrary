import { PersonalNotes } from "@/components/personal-notes";
import { WorkspaceNav } from "@/components/workspace-nav";
import { requireReader } from "@/lib/workspace-session";
import "../workspace.css";

export const metadata = { title: "আমার নোট", robots: { index: false, follow: false } };

export default async function NotesPage() {
  await requireReader("/notes/");
  return <div className="workspace"><WorkspaceNav label="পাঠকের নেভিগেশন" entries={[{ href: "/my-books/", label: "আমার বই" }, { href: "/notes/", label: "আমার নোট" }, { href: "/catalog/", label: "বই খুঁজুন" }]} />
    <section className="workspace-content"><p className="eyebrow">আপনার নিজের কথা</p><h1>আমার নোট</h1><p className="muted">বইয়ের দাগ, উদ্ধৃতি ও বুকমার্ক। পড়ার অনুমতি শেষ হলেও নিজের নোট এখানে থাকবে।</p><PersonalNotes /></section>
  </div>;
}
