// Translates raw API/network errors into user-friendly toast copy.
// Keep messages short, action-oriented, and free of jargon.

const FRIENDLY_BY_CODE = {
  network_error:
    "We couldn't reach the server. Check your connection and try again.",
  timeout: "The request took too long. Please try again.",
  unauthorized: "Your session has expired. Sign in again to continue.",
  forbidden: "You don't have permission to do that.",
  not_found: "We couldn't find what you were looking for.",
  conflict: "This conflicts with an existing record. Refresh and try again.",
  rate_limited: "Too many attempts. Please wait a moment before retrying.",
  validation_error:
    "Some fields need attention. Review the form and try again.",
  server_error: "Something went wrong on our side. Please try again shortly.",
  otp_required: "Enter your authenticator code to continue.",
  otp_invalid: "That code didn't match. Try again with a fresh code.",
};

const GENERIC_FALLBACK = "Something went wrong. Please try again.";
const MAX_MESSAGE_LENGTH = 200;

function looksLikeRawError(message) {
  if (!message) return true;
  return (
    /\b(traceback|exception|stacktrace|undefined|null|TypeError|SyntaxError)\b/i.test(
      message,
    ) || message.length > MAX_MESSAGE_LENGTH
  );
}

export function humanizeError(error, fallback = GENERIC_FALLBACK) {
  if (!error) {
    return fallback;
  }

  if (typeof error === "string") {
    return looksLikeRawError(error) ? fallback : error;
  }

  const code = error?.payload?.code || error?.code;
  if (code && FRIENDLY_BY_CODE[code]) {
    return FRIENDLY_BY_CODE[code];
  }

  const message = error?.message || error?.payload?.detail || "";

  const status = Number(error?.status ?? error?.payload?.status);
  if (status === 401) return FRIENDLY_BY_CODE.unauthorized;
  if (status === 403) return FRIENDLY_BY_CODE.forbidden;
  if (status === 404) {
    if (message && !looksLikeRawError(message) && message.toLowerCase() !== "not found") {
      return message;
    }
    return FRIENDLY_BY_CODE.not_found;
  }
  if (status === 409) return FRIENDLY_BY_CODE.conflict;
  if (status === 429) return FRIENDLY_BY_CODE.rate_limited;
  if (status >= 500) return FRIENDLY_BY_CODE.server_error;

  if (!message) return fallback;
  if (looksLikeRawError(message)) return fallback;
  return message;
}
