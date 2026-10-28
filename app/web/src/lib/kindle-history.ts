import type { KindleOperation } from "../api/types";

export const kindleHistoryKeys = ["q", "contributor", "category", "series", "state", "sort", "from_date", "to_date"] as const;
export type KindleHistoryFilter = Partial<Record<typeof kindleHistoryKeys[number], string>>;
export const kindleHistorySorts = {
  "-sent_at": "নতুন অনুরোধ আগে", sent_at: "পুরোনো অনুরোধ আগে", "-created_at": "নতুন বই আগে", created_at: "পুরোনো বই আগে", title: "বইয়ের নাম: অ–হ", "-title": "বইয়ের নাম: হ–অ",
};

export function kindleHistoryQuery(filters: KindleHistoryFilter) {
  return new URLSearchParams(kindleHistoryKeys.flatMap((key) => filters[key] ? [[key, filters[key]!]] : [])).toString();
}

export function kindleCanResend(state: KindleOperation["state"]) {
  return ["succeeded", "failed", "cancelled", "needs_attention"].includes(state);
}

export function kindleResendHref(operation: KindleOperation) {
  return `/kindle/books/${encodeURIComponent(operation.book.slug)}/?${new URLSearchParams({ resend: operation.id })}`;
}

export function kindleResendRecipients(previous: KindleOperation, current: readonly string[]) {
  return previous.recipients.map((recipient) => recipient.address).filter((address) => current.includes(address));
}
