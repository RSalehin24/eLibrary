import { cookies } from "next/headers";
import { adminLanguage, adminLanguageCookie } from "./admin-language";

export async function getAdminLanguage() {
  const stored = await cookies();
  return adminLanguage(stored.get("library-language")?.value ?? stored.get(adminLanguageCookie)?.value);
}
