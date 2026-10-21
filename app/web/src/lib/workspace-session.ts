import { cache } from "react";
import { notFound, redirect } from "next/navigation";
import { sessionRequest } from "@/api/server";
import type { WorkspaceSession } from "@/api/types";
import { cookies } from "next/headers";
import { workspaceSessionForCookies } from "./public-session";
import { selectedWorkspace, workspaceViewCookie } from "./workspace-view";

export const getWorkspaceSession = cache(async () => workspaceSessionForCookies((await cookies()).toString(), () => sessionRequest<WorkspaceSession>("auth/session/")));
export const getWorkspaceView = cache(async () => selectedWorkspace(await getWorkspaceSession(), (await cookies()).get(workspaceViewCookie)?.value));

export async function requireReader(path: string) {
  const session = await getWorkspaceSession();
  if (!session.authenticated) redirect(`/login/?next=${encodeURIComponent(path)}`);
  if (session.user?.totp_setup_required && path !== "/profile/") redirect(`/profile/?next=${encodeURIComponent(path)}`);
  return session;
}

export async function requireManagement(section: string, returnPath?: string) {
  const session = await requireReader(returnPath ?? `/manage/${section === "overview" ? "" : `${section}/`}`);
  if (!session.workspaces.management_sections.includes(section)) notFound();
  return session;
}
