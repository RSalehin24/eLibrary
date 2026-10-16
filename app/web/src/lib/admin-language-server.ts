import { cookies } from "next/headers";
import { adminLanguage, adminLanguageCookie } from "./admin-language";

export async function getAdminLanguage() {
  return adminLanguage((await cookies()).get(adminLanguageCookie)?.value);
}
