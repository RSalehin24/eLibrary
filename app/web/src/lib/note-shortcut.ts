export function submitNoteShortcut(event: Pick<KeyboardEvent, "key" | "ctrlKey" | "metaKey" | "altKey" | "repeat" | "preventDefault">, form: Pick<HTMLFormElement, "requestSubmit">) {
  if (event.key !== "Enter" || !(event.ctrlKey || event.metaKey) || event.altKey || event.repeat) return;
  event.preventDefault();
  form.requestSubmit();
}
