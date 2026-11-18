import { apiFetch, resolveAppUrl } from "../../api/client";

export function bookDetailFetch(path, options) {
  return apiFetch(path, options);
}

export function resolveBookDetailUrl(path) {
  return resolveAppUrl(path);
}
