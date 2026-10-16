import { apiMutation } from "./mutation";
import type { PasswordLink, PasswordLinkConfirmation, PasswordLinkInspection, PasswordLinkResult } from "./types";
import { parsePasswordLink } from "@/lib/password-link";

export const inspectPasswordLink = (ticket: PasswordLink) => apiMutation<PasswordLinkInspection>("auth/password-links/inspect/", { method: "POST", body: JSON.stringify(ticket) });
export const confirmPasswordLink = (values: PasswordLinkConfirmation) => apiMutation<PasswordLinkResult>("auth/password-links/confirm/", { method: "POST", body: JSON.stringify(values) });

export async function inspectPasswordLinkURL(url: string) {
  const ticket = parsePasswordLink(url);
  if (!ticket) throw new Error("Invalid password link.");
  const inspection = await inspectPasswordLink(ticket);
  return { ticket, inspection };
}
