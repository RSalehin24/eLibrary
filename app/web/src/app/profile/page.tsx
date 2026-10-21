import { localizeMetadata } from "@/lib/metadata-language";
import { SiteText } from "@/components/site-language";
import { sessionRequest } from "@/api/server";
import type { AccountProfile } from "@/api/types";
import { AccountSettings } from "@/components/account-settings";
import { queryValue, type RouteQuery } from "@/lib/route-query";
import { returnPath } from "@/lib/return-path";
import { getWorkspaceView, requireReader } from "@/lib/workspace-session";
import Link from "next/link";

export async function generateMetadata() { return localizeMetadata({ title: "প্রোফাইল ও নিরাপত্তা", robots: { index: false, follow: false } }); }

export default async function ProfilePage({ searchParams }: { searchParams: Promise<RouteQuery> }) {
  const session = await requireReader("/profile/");
  const view = await getWorkspaceView();
  const profile = await sessionRequest<AccountProfile>("auth/profile/");
  const nextPath = returnPath(queryValue(await searchParams, "next") || "/my-books/");
  return <div className="reader-page profile-page">
    <section className="workspace-content"><div className="profile-heading"><div><p className="eyebrow"><SiteText>{"আপনার অ্যাকাউন্ট"}</SiteText></p><h1><SiteText>{"প্রোফাইল ও নিরাপত্তা"}</SiteText></h1></div>
      {session.workspaces.manage && view === "admin" && <Link className="button button-quiet" href="/manage/"><SiteText>অ্যাডমিন প্যানেল </SiteText></Link>}</div>
      <AccountSettings initialProfile={profile} nextPath={nextPath} /></section>
  </div>;
}
