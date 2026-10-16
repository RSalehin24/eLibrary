import { InvitationForm } from "@/components/invitation-form";
import { requireManagement } from "@/lib/workspace-session";

export const metadata = { title: "পাঠককে আমন্ত্রণ জানান" };

export default async function InvitePage() {
  await requireManagement("users-access", "/manage/users-access/invite/");
  return <InvitationForm />;
}
