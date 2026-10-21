"use client";

import type { WorkspaceSession } from "@/api/types";
import { setWorkspaceView, type WorkspaceView } from "@/lib/workspace-view";
import { Icon } from "./icon";
import { SiteText, useSiteLanguage } from "./site-language";

export function WorkspaceViewSwitch({ session, target }: { session: WorkspaceSession; target: WorkspaceView }) {
  const { t } = useSiteLanguage();
  const label = target === "admin" ? "অ্যাডমিনে ফিরুন" : "পাঠকের ভিউ";
  if (!session.authenticated || !session.workspaces.manage || !session.user) return null;
  return <a className="button button-quiet workspace-view-switch" aria-label={t(label)} title={t(label)} href={target === "admin" ? "/manage/" : "/my-books/"}
    onClick={() => setWorkspaceView(session.user!.id, target)}>
    <Icon name={target === "admin" ? "overview" : "read"} /><SiteText>{label}</SiteText>
  </a>;
}
