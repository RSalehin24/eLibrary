import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import { LoginForm } from "@/components/login-form";
import { redirect } from "next/navigation";
import { getWorkspaceSession } from "@/lib/workspace-session";
import { returnPath } from "@/lib/return-path";
import { BrandMark } from "@/components/brand-mark";

export async function generateMetadata() { return localizeMetadata({ title: "প্রবেশ করুন", robots: { index: false, follow: false } }); }

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next = "/my-books/" } = await searchParams;
  const session = await getWorkspaceSession();
  if (session.authenticated) redirect(returnPath(next));
  return <div className="login-layout"><aside className="login-welcome"><BrandMark size={72} />
    <p className="eyebrow"><SiteText>{"বাংলা পাঠাগার"}</SiteText></p><h2><SiteText>{"আপনার পাঠের জগতে,"}</SiteText><br /><SiteText>{"স্বাগতম।"}</SiteText></h2>
    <p><SiteText>{"যে বইয়ে থেমেছিলেন, সেখান থেকেই আবার শুরু করুন। প্রিয় বই, নিজের নোট আর পড়ার স্মৃতি—সব এক জায়গায়।"}</SiteText></p>
    <span className="login-welcome-note"><SiteText>{"একটি বই। অনেক পৃথিবী।"}</SiteText></span>
  </aside><LoginForm nextPath={next} /></div>;
}
