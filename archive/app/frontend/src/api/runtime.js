import {
  API_BASE_URL,
  BACKEND_STATUS_EVENT,
  SERVICE_ERROR_WINDOW_MS,
  SESSION_EXPIRED_EVENT,
} from "./constants.js";

let sessionExpiredNotified = false;
let serviceFailureWindowStart = 0;
let serviceFailureCount = 0;
let backendOutageNotified = false;
let backendProbePromise = null;

function registerServiceFailure() {
  const now = Date.now();
  if (
    !serviceFailureWindowStart ||
    now - serviceFailureWindowStart > SERVICE_ERROR_WINDOW_MS
  ) {
    serviceFailureWindowStart = now;
    serviceFailureCount = 0;
  }
  serviceFailureCount += 1;
}

export function clearServiceFailureWindow() {
  serviceFailureWindowStart = 0;
  serviceFailureCount = 0;
}

export function notifyBackendRecovered() {
  if (!backendOutageNotified || typeof window === "undefined") {
    return;
  }

  backendOutageNotified = false;
  window.dispatchEvent(
    new CustomEvent(BACKEND_STATUS_EVENT, {
      detail: { state: "up" },
    }),
  );
}

function notifyBackendUnavailable(mode) {
  if (typeof window === "undefined") {
    return;
  }

  backendOutageNotified = true;
  window.dispatchEvent(
    new CustomEvent(BACKEND_STATUS_EVENT, {
      detail: { state: "down", mode },
    }),
  );
}

export function shouldTreatAsBackendUnavailable(status) {
  return [0, 502, 503, 504].includes(status);
}

function inferBackendMode(status, path) {
  const startupEndpoints = ["/csrf/", "/auth/session/"];
  const isStartupRequest = startupEndpoints.includes(path);
  const isLikelyRestarting =
    shouldTreatAsBackendUnavailable(status) &&
    (isStartupRequest || serviceFailureCount <= 3);
  return isLikelyRestarting ? "restarting" : "outage";
}

export async function probeBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/csrf/`, {
      credentials: "include",
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function evaluateBackendAvailability(status, path) {
  if (!shouldTreatAsBackendUnavailable(status)) {
    return;
  }

  if (backendProbePromise) {
    return backendProbePromise;
  }

  const mode = inferBackendMode(status, path);
  backendProbePromise = probeBackendHealth()
    .then((healthy) => {
      if (healthy) {
        notifyBackendRecovered();
      } else {
        notifyBackendUnavailable(mode);
      }
    })
    .finally(() => {
      backendProbePromise = null;
    });

  return backendProbePromise;
}

export function serviceUnavailableMessage(status, path) {
  registerServiceFailure();
  const isLikelyRestarting = inferBackendMode(status, path) === "restarting";
  if (isLikelyRestarting) {
    return "Please try again in a few minutes. The application is getting ready.";
  }
  return "There is an error. Please try again after a few hours.";
}

export function shouldNotifySessionExpired(status, path) {
  if (![401, 403].includes(status)) {
    return false;
  }

  const ignoredPaths = [
    "/auth/session/",
    "/auth/login/",
    "/auth/password-reset/",
  ];

  return !ignoredPaths.includes(path);
}

export function notifySessionExpired() {
  if (sessionExpiredNotified || typeof window === "undefined") {
    return;
  }

  sessionExpiredNotified = true;
  window.dispatchEvent(new CustomEvent(SESSION_EXPIRED_EVENT));
}

export function resetSessionExpiryNotification(path) {
  if (path === "/auth/login/" || path === "/auth/session/") {
    sessionExpiredNotified = false;
  }
}
