import { apiMutation, emptyMutation } from "./mutation";
import { notifyAccountChange } from "@/lib/account-channel";

type LoginCredentials = { email: string; password: string; otp_token?: string };

export async function signIn(credentials: LoginCredentials) {
  const result = await apiMutation("auth/login/", { method: "POST", body: JSON.stringify(credentials) });
  notifyAccountChange();
  return result;
}

export async function signOut() {
  await emptyMutation("auth/logout/", { method: "POST" });
  notifyAccountChange();
}
