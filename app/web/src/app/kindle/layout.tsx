import { WorkspaceAccount } from "@/components/workspace-account";
import { WorkspaceNav } from "@/components/workspace-nav";

export const metadata = { robots: { index: false, follow: false } };

export default function KindleLayout({ children }: { children: React.ReactNode }) {
  return <WorkspaceAccount><div className="workspace"><WorkspaceNav label="পাঠকের নেভিগেশন" entries={[{ href: "/my-books/", label: "আমার বই" }, { href: "/kindle/", label: "কিন্ডল" }, { href: "/notes/", label: "আমার নোট" }]} /><section className="workspace-content">{children}</section></div></WorkspaceAccount>;
}
