import { WorkspaceAccount } from "@/components/workspace-account";
import type { Metadata } from "next";
import { WorkspaceNav } from "@/components/workspace-nav";
import { getWorkspaceSession } from "@/lib/workspace-session";
import { getAdminLanguage } from "@/lib/admin-language-server";
import { AdminLanguageProvider } from "@/components/admin-language";
import "../workspace.css";
import "../entities.css";
import "../management.css";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function ManagementLayout({ children }: { children: React.ReactNode }) {
  const session = await getWorkspaceSession();
  const language = await getAdminLanguage();
  const entries = [{ href: "/manage/", label: "সারসংক্ষেপ" }];
  if (session.workspaces.management_sections.includes("sources")) entries.push({ href: "/manage/sources/", label: "উৎস" });
  if (session.workspaces.management_sections.includes("books")) entries.push({ href: "/manage/books/", label: "বই" });
  if (session.workspaces.management_sections.includes("books")) entries.push({ href: "/manage/entities/", label: "পরিচিতি" });
  if (session.workspaces.management_sections.includes("jobs")) entries.push({ href: "/manage/jobs/", label: "কাজ" });
  if (session.workspaces.management_sections.includes("automations")) entries.push({ href: "/manage/automations/", label: "স্বয়ংক্রিয় কাজ" });
  if (session.workspaces.management_sections.includes("users-access")) entries.push({ href: "/manage/users-access/", label: "ব্যবহারকারী ও অনুমতি" });
  entries.push({ href: "/my-books/", label: "পাঠকের জায়গায় যান" });
  return <WorkspaceAccount><AdminLanguageProvider initial={language}><div className="workspace"><WorkspaceNav entries={entries} label="পরিচালনার নেভিগেশন" />
    <section className="workspace-content">{children}</section></div></AdminLanguageProvider></WorkspaceAccount>;
}
