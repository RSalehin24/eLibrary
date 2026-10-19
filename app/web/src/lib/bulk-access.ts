import type { ManagedGrantCreate } from "../api/types";

export type BulkAccessKind = "account" | "book" | "category" | "author";
export type BulkAccessTarget = { id: string; name: string };
export type BulkAccessSelection = {
  kind: BulkAccessKind; scopes: ManagedGrantCreate["scope"][]; targets: BulkAccessTarget[];
  expiresAt: string | null; notes: string;
};
export const maximumBulkGrants = 100;
export const maximumBulkTargets = 20;

export function toggleAccessScope(scopes: ManagedGrantCreate["scope"][], scope: ManagedGrantCreate["scope"]) {
  if (scopes.includes(scope)) return scopes.filter((value) => value !== scope);
  const opposite = scope === "read:once" ? "read:durable" : scope === "read:durable" ? "read:once" : null;
  return [...scopes.filter((value) => value !== opposite), scope];
}

export function bulkGrantCount(selection: Pick<BulkAccessSelection, "kind" | "targets" | "scopes">) {
  return selection.scopes.length * (selection.kind === "account" ? 1 : selection.targets.length);
}

export function bulkGrantEntries(selection: BulkAccessSelection, identifier: () => string): ManagedGrantCreate[] {
  const targets = selection.kind === "account" ? [{ id: "", name: "" }] : selection.targets;
  return targets.flatMap((target) => selection.scopes.map((scope) => ({
    id: identifier(), scope, notes: selection.notes, expires_at: selection.expiresAt,
    ...(selection.kind === "book" ? { book: target.id } : selection.kind === "category" ? { category: target.id } : selection.kind === "author" ? { contributor: target.id } : {}),
  })));
}

export function dhakaDateTimeParts(value: string | null) {
  if (!value) return { date: "", time: "02:00" };
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: "Asia/Dhaka", year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).formatToParts(new Date(value));
  const part = (kind: Intl.DateTimeFormatPartTypes) => parts.find((entry) => entry.type === kind)?.value ?? "";
  return { date: `${part("year")}-${part("month")}-${part("day")}`, time: `${part("hour")}:${part("minute")}` };
}

export function dhakaDateTimeValue(date: string, time: string) {
  return date ? new Date(`${date}T${time}:00+06:00`).toISOString() : null;
}
