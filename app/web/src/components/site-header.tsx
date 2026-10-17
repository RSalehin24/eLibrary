import { siteName } from "@/lib/site";
import { AccountMenu } from "./account-menu";
import { BrandMark } from "./brand-mark";
import { SiteLanguageSwitch, SiteText, SiteLink } from "@/components/site-language";
import { SitePrimaryNav } from "./site-primary-nav";
import { getWorkspaceSession } from "@/lib/workspace-session";

export async function SiteHeader() {
  const session = await getWorkspaceSession();
  return <header className="site-header">
    <SiteLink href="/" className="brand" aria-label={siteName}><BrandMark /><span className="brand-copy"><span><SiteText>{siteName}</SiteText></span><small><SiteText>{"বাংলা বই, আপনার পৃথিবী"}</SiteText></small></span></SiteLink>
    <SitePrimaryNav canManageBooks={session.workspaces.management_sections.includes("books")} />
    <SiteLanguageSwitch /><AccountMenu initial={session} />
  </header>;
}
