export function formatRole(value) {
  return (value || "contributor").replace(/_/g, " ");
}

export function formatBookDate(value, options = {}) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...options,
  }).format(new Date(value));
}

export function formatBookDateTime(value) {
  if (!value) {
    return "";
  }
  return new Intl.DateTimeFormat("en", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

