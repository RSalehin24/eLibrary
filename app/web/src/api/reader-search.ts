export async function readChapterText(url: string, signal: AbortSignal) {
  const response = await fetch(url, { signal, credentials: "same-origin", cache: "no-store" });
  if (!response.ok) throw new Error("Reader chapter could not be loaded.");
  return response.text();
}
