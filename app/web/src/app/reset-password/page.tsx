import { redirect } from "next/navigation";
import { PasswordResetForm } from "@/components/password-reset-form";
import { getWorkspaceSession } from "@/lib/workspace-session";

export const metadata = { title: "পাসওয়ার্ড বদলানোর লিংক চাই", robots: { index: false, follow: false } };

export default async function PasswordResetPage() {
  if ((await getWorkspaceSession()).authenticated) redirect("/profile/");
  return <PasswordResetForm />;
}
