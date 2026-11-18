import { ensureCsrfCookie, getCookie } from "./csrf";
import { createApiError, createNetworkError } from "./errors";
import { API_BASE_URL } from "./constants";
import { parseResponse } from "./response";
import {
  clearServiceFailureWindow,
  notifyBackendRecovered,
  notifySessionExpired,
  resetSessionExpiryNotification,
  shouldNotifySessionExpired,
} from "./runtime";

export async function apiFetch(path, options = {}) {
  const method = (options.method || "GET").toUpperCase();
  const isFormData =
    typeof FormData !== "undefined" && options.body instanceof FormData;

  try {
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
      await ensureCsrfCookie();
    }

    const headers = new Headers(options.headers || {});
    if (!headers.has("Accept")) {
      headers.set("Accept", "application/json");
    }
    if (options.body && !isFormData && !headers.has("Content-Type")) {
      headers.set("Content-Type", "application/json");
    }
    if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
      const csrfToken = getCookie("csrftoken");
      if (csrfToken) {
        headers.set("X-CSRFToken", csrfToken);
      }
    }

    const response = await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      method,
      headers,
      credentials: "include",
      body: isFormData
        ? options.body
        : typeof options.body === "string"
          ? options.body
          : options.body
            ? JSON.stringify(options.body)
            : undefined,
    });

    const payload = await parseResponse(response);
    if (!response.ok) {
      if (shouldNotifySessionExpired(response.status, path)) {
        notifySessionExpired();
      }
      throw createApiError({ status: response.status, payload, path });
    }

    clearServiceFailureWindow();
    notifyBackendRecovered();
    resetSessionExpiryNotification(path);
    return payload;
  } catch (error) {
    if (typeof error?.status === "number") {
      throw error;
    }
    throw createNetworkError(path);
  }
}
