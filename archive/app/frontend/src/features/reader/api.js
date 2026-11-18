import { apiFetch, resolveAppUrl } from "../../api/client";

export function readerFetch(path, options) {
  return apiFetch(path, options);
}

export function resolveReaderUrl(path) {
  return resolveAppUrl(path);
}
