export type ReaderAppearance = { fontSize: number; theme: "paper" | "sepia" | "dark" };
export type ReadingAnchor = { element: Element; offset: number };
const THEMES = { paper: ["#fbfaf6", "#20372e"], sepia: ["#f1e7d1", "#3e3222"], dark: ["#18221e", "#eee9dd"] };

export function applyAppearance(document: Document, appearance: ReaderAppearance) {
  const style = document.getElementById("library-reader-appearance") ?? document.createElement("style");
  style.id = "library-reader-appearance";
  const [background, color] = THEMES[appearance.theme];
  style.textContent = `html { color-scheme:${appearance.theme === "dark" ? "dark" : "light"}; scroll-behavior:auto; background:${background}!important; }
    body { max-width:740px!important; margin:auto!important; padding:24px 20px 60px!important; color:${color}!important; background:${background}!important; overflow-wrap:anywhere; line-height:1.9!important; font-size:${appearance.fontSize}px!important; font-family:"Noto Serif Bengali","Bangla Sangam MN",serif!important; }
    img,svg,video,table { max-width:100%!important; } a { color:inherit!important; } :focus-visible { outline:3px solid #b1792f; }
    mark[data-library-highlight] { background:#f8df7b!important; color:#20372e!important; }
    mark[data-color=green] { background:#b5dcad!important; } mark[data-color=blue] { background:#b4d5f1!important; }
    mark[data-color=pink] { background:#f2bbcd!important; } mark[data-color=underline] { background:transparent!important; color:inherit!important; text-decoration:underline 2px #b1792f; }`;
  document.head.append(style);
}

export function scrollFraction(document: Document) {
  const root = document.scrollingElement ?? document.documentElement;
  const maximum = root.scrollHeight - root.clientHeight;
  return maximum > 0 ? Math.min(1, Math.max(0, root.scrollTop / maximum)) : 1;
}

export function restoreScroll(document: Document, fraction: number) {
  const root = document.scrollingElement ?? document.documentElement;
  root.scrollTop = (root.scrollHeight - root.clientHeight) * fraction;
}

export function visibleAnchor(document: Document): ReadingAnchor | null {
  const element = Array.from(document.querySelectorAll("h1,h2,h3,p,li,blockquote,figure")).find((candidate) => candidate.getBoundingClientRect().bottom > 0);
  if (!element) return null;
  const rectangle = element.getBoundingClientRect();
  return { element, offset: -rectangle.top / Math.max(rectangle.height, 1) };
}

export function restoreAnchor(document: Document, anchor: ReadingAnchor | null, fraction: number) {
  if (!anchor?.element.isConnected || anchor.element.ownerDocument !== document) { restoreScroll(document, fraction); return; }
  const root = document.scrollingElement ?? document.documentElement;
  const rectangle = anchor.element.getBoundingClientRect();
  root.scrollTop += rectangle.top + rectangle.height * anchor.offset;
}
