export function stripHtmlTags(value) {
  return value.replace(/<[^>]*>/g, " ");
}

export function normalizePlainText(value) {
  if (typeof value !== "string") {
    return "";
  }

  const trimmed = value.trim();
  if (!trimmed) {
    return "";
  }

  return stripHtmlTags(trimmed).replace(/\s+/g, " ").trim();
}

function firstMeaningfulPathSegment(path) {
  if (!Array.isArray(path) || !path.length) {
    return "";
  }

  return (
    [...path].reverse().find(
      (segment) => typeof segment === "string" && !/^\d+$/.test(segment),
    ) || ""
  );
}

function collectPayloadIssues(payload, issues, path = []) {
  if (issues.length) {
    return issues;
  }

  if (typeof payload === "string") {
    const message = normalizePlainText(payload);
    if (message) {
      issues.push({
        field: firstMeaningfulPathSegment(path),
        message,
      });
    }
    return issues;
  }

  if (Array.isArray(payload)) {
    for (const entry of payload) {
      collectPayloadIssues(entry, issues, path);
      if (issues.length) {
        break;
      }
    }
    return issues;
  }

  if (!payload || typeof payload !== "object") {
    return issues;
  }

  for (const key of ["detail", "message", "non_field_errors"]) {
    if (!(key in payload)) {
      continue;
    }
    collectPayloadIssues(payload[key], issues, path);
    if (issues.length) {
      return issues;
    }
  }

  for (const [key, value] of Object.entries(payload)) {
    if (["detail", "message", "non_field_errors", "code"].includes(key)) {
      continue;
    }
    collectPayloadIssues(value, issues, [...path, key]);
    if (issues.length) {
      return issues;
    }
  }

  return issues;
}

export function firstPayloadIssue(payload) {
  return collectPayloadIssues(payload, [])[0] || null;
}

export function payloadMessage(payload) {
  const issue = firstPayloadIssue(payload);
  if (!issue) {
    return "";
  }
  return issue.message;
}

export function humanizeFieldLabel(field) {
  if (typeof field !== "string" || !field.trim()) {
    return "";
  }

  return field
    .split(".")
    .pop()
    .replace(/_/g, " ")
    .replace(/\s+/g, " ")
    .trim()
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function payloadFieldMessage(payload, labelMap = {}) {
  const issue = firstPayloadIssue(payload);
  if (!issue) {
    return "";
  }

  const label = labelMap[issue.field] || humanizeFieldLabel(issue.field);
  return label ? `${label}: ${issue.message}` : issue.message;
}
