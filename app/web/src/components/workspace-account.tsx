import type { ReactNode } from "react";
import { getWorkspaceSession } from "@/lib/workspace-session";
import { AccountSnapshot } from "./account-snapshot";

export async function WorkspaceAccount({ children }: { children: ReactNode }) {
  const session = await getWorkspaceSession();
  return <AccountSnapshot identity={session.user?.id ?? null}>{children}</AccountSnapshot>;
}
