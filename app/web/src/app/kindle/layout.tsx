import { localizeMetadata } from "@/lib/metadata-language";
import { WorkspaceAccount } from "@/components/workspace-account";

export async function generateMetadata() { return localizeMetadata({ robots: { index: false, follow: false } }); }

export default function KindleLayout({ children }: { children: React.ReactNode }) {
  return <WorkspaceAccount><section className="reader-page kindle-page">{children}</section></WorkspaceAccount>;
}
