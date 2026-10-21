import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import { LoginForm } from "@/components/login-form";
import { redirect } from "next/navigation";
import { getWorkspaceSession } from "@/lib/workspace-session";
import { returnPath } from "@/lib/return-path";
import { BrandLogo } from "@/components/brand-logo";
import { cookies } from "next/headers";
import { workspaceHome, workspaceViewCookie } from "@/lib/workspace-view";

export async function generateMetadata() { return localizeMetadata({ title: "প্রবেশ করুন", robots: { index: false, follow: false } }); }

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next } = await searchParams;
  const session = await getWorkspaceSession();
  if (session.authenticated) {
    const home = workspaceHome(session, (await cookies()).get(workspaceViewCookie)?.value);
    redirect(returnPath(next ?? home, home));
  }
  return <div className="login-layout"><aside className="login-welcome"><BrandLogo />
    <h2><SiteText>{"আপনার পাঠের জগতে,"}</SiteText><br /><SiteText>{"স্বাগতম।"}</SiteText></h2>
    <p><SiteText>{"যে বইয়ে থেমেছিলেন, সেখান থেকেই আবার শুরু করুন। প্রিয় বই, নিজের নোট আর পড়ার স্মৃতি—সব এক জায়গায়।"}</SiteText></p>
    <span className="login-welcome-note"><SiteText>{"একটি বই। অনেক পৃথিবী।"}</SiteText></span>
  </aside><LoginForm nextPath={next} /></div>;
}
