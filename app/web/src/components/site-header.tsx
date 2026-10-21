import { cookies } from "next/headers";
import { AccountMenu } from "./account-menu";
import { BrandLogo } from "./brand-logo";
import { SiteLanguageSwitch, SiteLink } from "@/components/site-language";
import { SitePrimaryNav } from "./site-primary-nav";
import { getWorkspaceSession } from "@/lib/workspace-session";
import { selectedWorkspace, workspaceViewCookie } from "@/lib/workspace-view";
import { WorkspaceViewSwitch } from "./workspace-view-switch";

export async function SiteHeader() {
  const session = await getWorkspaceSession();
  const view = selectedWorkspace(session, (await cookies()).get(workspaceViewCookie)?.value);
  return <header className="site-header" data-workspace={view}>
    <SiteLink href={view === "admin" ? "/manage/" : "/"} className="brand" aria-label="বাংলা পাঠাগার"><BrandLogo /></SiteLink>
    <SiteLanguageSwitch />
    <div className="site-header-account"><WorkspaceViewSwitch session={session} target={view === "admin" ? "reader" : "admin"} /><AccountMenu initial={session} /></div>
    <SitePrimaryNav view={view} managementSections={session.workspaces.management_sections} />
  </header>;
}
