import { localizeMetadata } from "@/lib/metadata-language";
import { requireManagement } from "@/lib/workspace-session";
import { sessionRequest } from "@/api/server";
import type { ManagementOverview } from "@/api/types";
import { ManagementOverviewWorkspace } from "@/components/management-overview";
import Link from "next/link";
import { AdminNavigation, AdminText } from "@/components/admin-language";

export async function generateMetadata() { return localizeMetadata({ title: "পরিচালনা" }); }

export default async function ManagementPage() {
  const session = await requireManagement("overview");
  const initial = await sessionRequest<ManagementOverview>("manage/overview/");
  return <><h1><AdminText>পরিচালনা</AdminText></h1>
    <AdminNavigation className="management-shortcuts" label="পরিচালনার প্রধান কাজ">
      {session.workspaces.management_sections.includes("sources") && <Link href="/manage/sources/"><strong><AdminText>উৎস থেকে বই আনুন</AdminText></strong><span><AdminText>বইয়ের তালিকা থেকে নির্বাচন করুন।</AdminText></span></Link>}
      {session.workspaces.can_create_books && <Link href="/manage/books/new/"><strong><AdminText>নিজে বই যোগ করুন</AdminText></strong><span><AdminText>EPUB আপলোড</AdminText></span></Link>}
      {session.workspaces.management_sections.includes("jobs") && <Link href="/manage/jobs/"><strong><AdminText>কাজের অগ্রগতি</AdminText></strong><span><AdminText>অপেক্ষমাণ, চলমান ও ব্যর্থ কাজ দেখুন।</AdminText></span></Link>}
    </AdminNavigation>
    <ManagementOverviewWorkspace initial={initial} />
  </>;
}
