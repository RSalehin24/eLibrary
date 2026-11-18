import { API_BASE_URL } from "./constants";

let csrfReadyPromise = null;

export function getCookie(name) {
  const match = document.cookie.match(new RegExp(`(^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[2]) : "";
}

export async function ensureCsrfCookie() {
  if (!csrfReadyPromise) {
    csrfReadyPromise = fetch(`${API_BASE_URL}/csrf/`, {
      credentials: "include",
    }).finally(() => {
      csrfReadyPromise = null;
    });
  }
  return csrfReadyPromise;
}
