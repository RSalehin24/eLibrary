import type { PasswordLink } from "../api/types";

export function parsePasswordLink(value: string): PasswordLink | null {
  const url = new URL(value);
  const fragment = new URLSearchParams(url.hash.slice(1));
  const parameters = fragment.size ? fragment : url.searchParams;
  const uid = parameters.get("uid"), token = parameters.get("token");
  if (parameters.getAll("uid").length !== 1 || parameters.getAll("token").length !== 1 || !uid || !token || uid.length > 256 || token.length > 256) return null;
  return { uid, token };
}
