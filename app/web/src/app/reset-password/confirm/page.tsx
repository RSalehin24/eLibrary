import { localizeMetadata } from "@/lib/metadata-language";
import { PasswordLinkForm } from "@/components/password-link-form";

export async function generateMetadata() { return localizeMetadata({ title: "নতুন পাসওয়ার্ড দিন", robots: { index: false, follow: false } }); }

export default function ResetPasswordConfirmPage() {
  return <PasswordLinkForm />;
}
