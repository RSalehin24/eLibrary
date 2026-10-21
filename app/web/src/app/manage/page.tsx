import { notFound, redirect } from "next/navigation";
import { requireReader } from "@/lib/workspace-session";
import { managementHome } from "@/lib/management-navigation";

export default async function ManagementPage() {
  const session = await requireReader("/manage/");
  if (!session.workspaces.manage) notFound();
  redirect(managementHome(session.workspaces.management_sections));
}
