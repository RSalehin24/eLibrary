import { LoginForm } from "@/components/login-form";
import { redirect } from "next/navigation";
import { getWorkspaceSession } from "@/lib/workspace-session";
import { returnPath } from "@/lib/return-path";
import { BrandMark } from "@/components/brand-mark";

export const metadata = { title: "প্রবেশ করুন", robots: { index: false, follow: false } };

export default async function LoginPage({ searchParams }: { searchParams: Promise<{ next?: string }> }) {
  const { next = "/my-books/" } = await searchParams;
  const session = await getWorkspaceSession();
  if (session.authenticated) redirect(returnPath(next));
  return <div className="login-layout"><aside className="login-welcome"><BrandMark size={72} />
    <p className="eyebrow">বাংলা পাঠাগার</p><h2>আপনার পাঠের জগতে,<br />স্বাগতম।</h2>
    <p>যে বইয়ে থেমেছিলেন, সেখান থেকেই আবার শুরু করুন। প্রিয় বই, নিজের নোট আর পড়ার স্মৃতি—সব এক জায়গায়।</p>
    <span className="login-welcome-note">একটি বই। অনেক পৃথিবী।</span>
  </aside><LoginForm nextPath={next} /></div>;
}
