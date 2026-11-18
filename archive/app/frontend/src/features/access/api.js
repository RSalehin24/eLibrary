import { apiFetch } from "../../api/client";

export function accessFetch(path, options) {
  return apiFetch(path, options);
}
