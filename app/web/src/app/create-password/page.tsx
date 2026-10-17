import { localizeMetadata } from "@/lib/metadata-language";
import { PasswordLinkForm } from "@/components/password-link-form";

export async function generateMetadata() { return localizeMetadata({ title: "পাসওয়ার্ড তৈরি করুন", robots: { index: false, follow: false } }); }

export default function CreatePasswordPage() {
  return <PasswordLinkForm />;
}
