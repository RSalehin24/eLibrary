import type { ReactNode } from "react";
import { WorkspaceAccount } from "@/components/workspace-account";

export default function AccountLayout({ children }: { children: ReactNode }) {
  return <WorkspaceAccount>{children}</WorkspaceAccount>;
}
