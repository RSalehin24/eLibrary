import { AdminText } from "@/components/admin-language";
import Link from "next/link";
import { AutomationForm } from "@/components/automation-form";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "নতুন স্বয়ংক্রিয় সময়সূচি" };

export default async function NewAutomationPage() {
  await requireManagement("automations");
  return <><Link className="text-link" href="/manage/automations/"><AdminText>{"← সময়সূচিতে ফিরুন"}</AdminText></Link><h1><AdminText>{"নতুন সময়সূচি"}</AdminText></h1><AutomationForm /></>;
}
