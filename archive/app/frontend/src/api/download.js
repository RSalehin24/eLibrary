import { API_BASE_URL } from "./constants";
import { fallbackDownloadFilename, filenameFromDisposition, parseResponse } from "./response";

export async function downloadApiFile(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (!headers.has("Accept")) {
    headers.set("Accept", "*/*");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    method: options.method || "GET",
    headers,
    credentials: "include",
  });

  if (!response.ok) {
    const payload = await parseResponse(response);
    const error = new Error(
      typeof payload === "string"
        ? payload
        : payload.detail || "Request failed.",
    );
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  const contentType = response.headers.get("content-type") || "";
  const disposition = response.headers.get("content-disposition") || "";
  if (contentType.includes("application/json") && !disposition) {
    const payload = await response.json();
    const error = new Error(
      typeof payload === "string"
        ? payload
        : payload.detail || "Download failed.",
    );
    error.status = response.status;
    error.payload = payload;
    throw error;
  }

  const blob = await response.blob();
  const filename =
    filenameFromDisposition(disposition) ||
    fallbackDownloadFilename(contentType);
  const objectUrl = window.URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 1000);
}
