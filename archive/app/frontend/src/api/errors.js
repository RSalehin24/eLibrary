import { payloadMessage } from "./text.js";
import {
  evaluateBackendAvailability,
  serviceUnavailableMessage,
  shouldTreatAsBackendUnavailable,
} from "./runtime.js";

export function createApiError({ status, payload, path }) {
  const message = payloadMessage(payload);
  let resolvedMessage = message || "Request failed.";

  if (shouldTreatAsBackendUnavailable(status)) {
    void evaluateBackendAvailability(status, path);
    resolvedMessage = message || serviceUnavailableMessage(status, path);
  } else if ([500, 501].includes(status)) {
    resolvedMessage = message || "Request failed.";
  }

  const error = new Error(resolvedMessage);
  error.status = status;
  error.payload = payload;
  return error;
}

export function createNetworkError(path) {
  void evaluateBackendAvailability(0, path);
  const error = new Error(serviceUnavailableMessage(0, path));
  error.status = 0;
  error.payload = null;
  return error;
}
