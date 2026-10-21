import { localizeMetadata } from "@/lib/metadata-language";
import { WorkspaceAccount } from "@/components/workspace-account";
import "../workspace.css";

export async function generateMetadata() { return localizeMetadata({ robots: { index: false, follow: false } }); }

export default function LibraryLayout({ children }: { children: React.ReactNode }) {
  return <WorkspaceAccount><div className="reader-page">{children}</div></WorkspaceAccount>;
}
