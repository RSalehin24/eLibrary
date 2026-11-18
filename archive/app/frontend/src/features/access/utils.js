import { payloadFieldMessage } from "../../api/text.js";

export function generateSuggestedPassword(length = 18) {
  const characters =
    "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*";
  const randomValues = new Uint32Array(length);
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(randomValues);
  } else {
    for (let index = 0; index < length; index += 1) {
      randomValues[index] = Math.floor(Math.random() * characters.length);
    }
  }
  return Array.from(
    randomValues,
    (value) => characters[value % characters.length],
  ).join("");
}

export function sortValues(values) {
  return [...values].sort((left, right) => `${left}`.localeCompare(`${right}`));
}

export function formatApiError(error, labelMap = {}) {
  if (
    error?.payload &&
    typeof error.payload === "object" &&
    !Array.isArray(error.payload)
  ) {
    const fieldMessage = payloadFieldMessage(error.payload, labelMap);
    if (fieldMessage) {
      return fieldMessage;
    }
  }
  return error.message;
}

export function getAccountAccessLabels(entry, scopeLabelMap) {
  return sortValues(
    (entry.global_scopes || []).map(
      (scope) => scopeLabelMap.get(scope) || scope,
    ),
  );
}

export function formatAccountAccess(entry, scopeLabelMap) {
  const labels = getAccountAccessLabels(entry, scopeLabelMap);
  return labels.length ? labels.join(", ") : "-";
}

export function grantTargetField(targetType) {
  if (targetType === "category") {
    return "category";
  }
  if (targetType === "writer") {
    return "contributor";
  }
  return "book";
}
