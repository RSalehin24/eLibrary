export type ReaderAppearance = { fontSize: number; theme: "paper" | "sepia" | "dark"; view: "scroll" | "single" | "spread"; font: "serif" | "sans" | "publisher"; lineHeight: number; width: number };
export const defaultReaderAppearance: ReaderAppearance = { fontSize: 20, theme: "paper", view: "scroll", font: "serif", lineHeight: 1.9, width: 800 };

export function readerAppearanceShortcut(event: KeyboardEvent, appearance: ReaderAppearance): ReaderAppearance | null {
  if (event.defaultPrevented || event.altKey || !(event.ctrlKey || event.metaKey)) return null;
  if ((event.target as Element | null)?.closest?.('input,textarea,select,[contenteditable="true"],[contenteditable=""],[role="textbox"]')) return null;
  const themes: Record<string, ReaderAppearance["theme"]> = { "1": "paper", "2": "sepia", "3": "dark" };
  if (themes[event.key]) return { ...appearance, theme: themes[event.key] };
  if (["+", "=", "-"].includes(event.key)) return checkedReaderAppearance({ ...appearance, fontSize: appearance.fontSize + (event.key === "-" ? -2 : 2) });
  return null;
}

export function checkedReaderAppearance(value: unknown): ReaderAppearance {
  const data = typeof value === "object" && value !== null ? value as Record<string, unknown> : {};
  return {
    fontSize: typeof data.fontSize === "number" && Number.isFinite(data.fontSize) ? Math.max(16, Math.min(40, data.fontSize)) : 20,
    theme: data.theme === "sepia" || data.theme === "dark" ? data.theme : "paper",
    view: data.view === "single" || data.view === "spread" ? data.view : "scroll",
    font: data.font === "sans" || data.font === "publisher" ? data.font : "serif",
    lineHeight: typeof data.lineHeight === "number" && Number.isFinite(data.lineHeight) ? Math.max(1.4, Math.min(2.4, data.lineHeight)) : 1.9,
    width: typeof data.width === "number" && [640, 800, 1040].includes(data.width) ? data.width : 800,
  };
}
