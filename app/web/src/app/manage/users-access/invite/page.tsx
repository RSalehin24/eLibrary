import { localizeMetadata } from "@/lib/metadata-language";
import { InvitationForm } from "@/components/invitation-form";
import { requireManagement } from "@/lib/workspace-session";

export async function generateMetadata() { return localizeMetadata({ title: "পাঠককে আমন্ত্রণ জানান" }); }

export default async function InvitePage() {
  const session = await requireManagement("users-access", "/manage/users-access/invite/");
  return <InvitationForm canSetPassword={session.user?.is_superuser ?? false} />;
}
