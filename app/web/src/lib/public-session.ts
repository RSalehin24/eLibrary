import type { WorkspaceSession } from "@/api/types";

export function workspaceSessionForCookies(cookieHeader: string, load: () => Promise<WorkspaceSession>): Promise<WorkspaceSession> {
  if (cookieHeader) return load();
  // A static shell has no session credentials; the client obtains CSRF state online.
  return Promise.resolve({ authenticated: false, user: null, workspaces: { reader: true, manage: false, management_sections: [], can_create_books: false }, csrf_token: "" });
}
