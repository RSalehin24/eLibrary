export type ReaderMatch = { chapter: number; start: number; end: number; excerpt: string };
export function chapterMatches(text: string, query: string, chapter: number): ReaderMatch[] {
  const matches: ReaderMatch[] = [], normalized = text.toLocaleLowerCase(), term = query.trim().toLocaleLowerCase();
  if (!term) return matches;
  let start = normalized.indexOf(term);
  while (start >= 0 && matches.length < 100) {
    matches.push({ chapter, start, end: start + term.length, excerpt: text.slice(Math.max(0, start - 45), start + term.length + 90).replace(/\s+/g, " ") });
    start = normalized.indexOf(term, start + Math.max(term.length, 1));
  }
  return matches;
}

export function inertChapterText(markup: string) {
  const template = document.createElement("template");
  template.innerHTML = markup;
  const xml = new DOMParser().parseFromString(markup, "application/xhtml+xml");
  const body = xml.querySelector("parsererror") ? template.content.querySelector("body") ?? template.content : xml.querySelector("body") ?? xml;
  body.querySelectorAll("script,style,noscript,template").forEach(element => element.remove());
  const walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT);
  let text = "";
  for (let node = walker.nextNode(); node; node = walker.nextNode()) text += node.textContent;
  return text;
}
