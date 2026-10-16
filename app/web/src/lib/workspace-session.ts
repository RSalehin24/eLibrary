import { cache } from "react";
import { notFound, redirect } from "next/navigation";
import { sessionRequest } from "@/api/server";
import type { WorkspaceSession } from "@/api/types";

export const getWorkspaceSession = cache(() => sessionRequest<WorkspaceSession>("auth/session/"));

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
