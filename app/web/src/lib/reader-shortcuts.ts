const tools: Readonly<Record<string, string>> = { t: "contents", s: "settings", "/": "search" };

export function activateReaderTool(event: KeyboardEvent, workspace: HTMLElement | null) {
  if (event.defaultPrevented || event.repeat || event.ctrlKey || event.metaKey || event.altKey || event.shiftKey) return;
  if ((event.target as Element | null)?.closest?.('input,textarea,select,audio,video,[contenteditable],[role="textbox"]')) return;
  const tool = tools[event.key.toLowerCase()];
  const button = tool && workspace?.querySelector<HTMLButtonElement>(`[data-reader-tool="${tool}"]`);
  if (!button) return;
  event.preventDefault();
  button.click();
}
