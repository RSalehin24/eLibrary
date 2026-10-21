import type { WorkspaceSession } from "../api/types";

export const workspaceViewCookie = "library-workspace-view";
export type WorkspaceView = "admin" | "reader";

export function selectedWorkspace(session: WorkspaceSession, preference?: string): WorkspaceView {
  if (!session.authenticated || !session.workspaces.manage) return "reader";
  return preference === `${session.user?.id}:reader` ? "reader" : "admin";
}

export function workspaceHome(session: WorkspaceSession, preference?: string) {
  if (session.user?.totp_setup_required) return "/profile/";
  return selectedWorkspace(session, preference) === "admin" ? "/manage/" : "/my-books/";
}

export function setWorkspaceView(accountId: string | number, view: WorkspaceView) {
  const secure = location.protocol === "https:" ? "; Secure" : "";
  document.cookie = `${workspaceViewCookie}=${encodeURIComponent(String(accountId))}:${view}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`;
}

export function clearWorkspaceView() {
  document.cookie = `${workspaceViewCookie}=; Path=/; Max-Age=0; SameSite=Lax`;
}
