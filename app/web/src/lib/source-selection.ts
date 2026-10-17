import type { SourceEntry } from "../api/types";

export type SelectedSource = { entry: SourceEntry; operationId: string };
export const sourceSelectionLimit = 100;

export function toggleSourcePage(current: Record<string, SelectedSource>, entries: SourceEntry[]) {
  const available = entries.filter((entry) => entry.can_process || current[entry.id]);
  const clear = available.every((entry) => current[entry.id]);
  const next = { ...current };
  for (const entry of available) {
    if (clear) delete next[entry.id];
    else if (!next[entry.id] && Object.keys(next).length < sourceSelectionLimit) next[entry.id] = { entry, operationId: crypto.randomUUID() };
  }
  return next;
}
