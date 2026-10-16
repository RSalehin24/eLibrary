import { PasswordLinkForm } from "@/components/password-link-form";

export const metadata = { title: "নতুন পাসওয়ার্ড দিন", robots: { index: false, follow: false } };

export default function ResetPasswordConfirmPage() {
  return <PasswordLinkForm />;
}
