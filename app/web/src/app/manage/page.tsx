import { requireManagement } from "@/lib/workspace-session";
import { sessionRequest } from "@/api/server";
import type { ManagementOverview } from "@/api/types";
import { ManagementOverviewWorkspace } from "@/components/management-overview";
import Link from "next/link";
import { AdminText } from "@/components/admin-language";

export const metadata = { title: "পরিচালনা" };

export default async function ManagementPage() {
  const session = await requireManagement("overview");
  const initial = await sessionRequest<ManagementOverview>("manage/overview/");
  return <><h1><AdminText>পরিচালনা</AdminText></h1>
    <nav className="management-shortcuts" aria-label="পরিচালনার প্রধান কাজ">
      {session.workspaces.management_sections.includes("sources") && <Link href="/manage/sources/"><strong><AdminText>উৎস থেকে বই আনুন</AdminText> <span aria-hidden="true">→</span></strong><span><AdminText>বইয়ের তালিকা থেকে নির্বাচন করুন।</AdminText></span></Link>}
      {session.workspaces.can_create_books && <Link href="/manage/books/new/"><strong><AdminText>নিজে বই যোগ করুন</AdminText> <span aria-hidden="true">→</span></strong><span><AdminText>EPUB আপলোড করুন বা ছাপা বই যোগ করুন।</AdminText></span></Link>}
      {session.workspaces.management_sections.includes("jobs") && <Link href="/manage/jobs/"><strong><AdminText>কাজের অগ্রগতি</AdminText> <span aria-hidden="true">→</span></strong><span><AdminText>অপেক্ষমাণ, চলমান ও ব্যর্থ কাজ দেখুন।</AdminText></span></Link>}
    </nav>
    <ManagementOverviewWorkspace initial={initial} />
  </>;
}
