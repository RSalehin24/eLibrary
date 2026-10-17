import { localizeMetadata } from "@/lib/metadata-language";
import { WorkspaceAccount } from "@/components/workspace-account";
import { WorkspaceNav } from "@/components/workspace-nav";
import "../workspace.css";

export async function generateMetadata() { return localizeMetadata({ robots: { index: false, follow: false } }); }

export default function LibraryLayout({ children }: { children: React.ReactNode }) {
  return <WorkspaceAccount><div className="workspace"><WorkspaceNav label="পাঠকের নেভিগেশন"
    entries={[{ href: "/my-books/", label: "আমার বই" }, { href: "/kindle/", label: "কিন্ডল" }, { href: "/notes/", label: "আমার নোট" }, { href: "/catalog/", label: "বই খুঁজুন" }]} />
    <section className="workspace-content">{children}</section></div></WorkspaceAccount>;
}
