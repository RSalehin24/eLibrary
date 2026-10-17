import type { ReaderAppearance } from "./reader-preferences";
export type { ReaderAppearance } from "./reader-preferences";
export type ReadingAnchor = { node: Node; offset: number; top: number };
const THEMES = { paper: ["#fbfaf6", "#20372e"], sepia: ["#f1e7d1", "#3e3222"], dark: ["#18221e", "#eee9dd"] };

export function applyAppearance(document: Document, appearance: ReaderAppearance) {
  const style = document.getElementById("library-reader-appearance") ?? document.createElement("style");
  style.id = "library-reader-appearance";
  const [background, color] = THEMES[appearance.theme];
  const paged = appearance.view !== "scroll";
  const columns = appearance.view === "spread" && document.documentElement.clientWidth >= 900 ? 2 : 1;
  const sourceBody = document.querySelector<HTMLDivElement>("body > div");
  if (sourceBody?.style.margin === "40px" && sourceBody.style.fontFamily.includes("Kalpurush")) sourceBody.classList.add("library-source-content");
  document.documentElement.dataset.readerView = appearance.view;
  const font = appearance.font === "sans" ? 'font-family:"Noto Sans Bengali",system-ui,sans-serif!important;' : appearance.font === "serif" ? 'font-family:"Noto Serif Bengali","Bangla Sangam MN",serif!important;' : "";
  style.textContent = `* { box-sizing:border-box; } html { color-scheme:${appearance.theme === "dark" ? "dark" : "light"}; scroll-behavior:auto; background:${background}!important; overflow:${paged ? "hidden" : "auto"}!important; overscroll-behavior:none; }
    body { max-width:${paged ? "none" : appearance.width + "px"}!important; width:100%!important; margin:auto!important; padding:24px!important; color:${color}!important; background:${background}!important; overflow-wrap:anywhere; line-height:${appearance.lineHeight}!important; font-size:${appearance.fontSize}px!important; ${font}
    ${paged ? `height:${document.documentElement.clientHeight}px!important; column-width:${(document.documentElement.clientWidth - 48 - (columns - 1) * 48) / columns}px!important; column-gap:48px!important; column-fill:auto!important;` : "height:auto!important; column-width:auto!important;"} }
    body p,body li,body blockquote,body td,body div,body span { font-size:inherit!important; line-height:inherit!important; color:inherit!important; background:transparent!important; ${font} }
    body h1 { font-size:1.7em!important; } body h2 { font-size:1.4em!important; } body h3 { font-size:1.2em!important; }
    body>.library-source-content { margin:0!important; }
    img,svg,video,table { max-width:100%!important; } img,svg { max-height:${paged ? "75vh" : "none"}!important; object-fit:contain; } a { color:inherit!important; } :focus-visible { outline:3px solid #b1792f; }
    ${paged ? "html::after { content:''; position:absolute; top:0; left:var(--reader-extent,0); width:1px; height:1px; pointer-events:none; }" : ""}
    mark[data-library-highlight] { background:#f8df7b!important; color:#20372e!important; }
    mark[data-color=green] { background:#b5dcad!important; } mark[data-color=blue] { background:#b4d5f1!important; }
    mark[data-color=pink] { background:#f2bbcd!important; } mark[data-color=underline] { background:transparent!important; color:inherit!important; text-decoration:underline 2px #b1792f; }`;
  document.documentElement.style.removeProperty("--reader-extent");
  document.head.append(style);
  if (paged) {
    const root = document.scrollingElement ?? document.documentElement;
    document.documentElement.style.setProperty("--reader-extent", `${Math.ceil(root.scrollWidth / root.clientWidth) * root.clientWidth - 1}px`);
  }
}

export function isPaged(document: Document) { return ["single", "spread"].includes(document.documentElement.dataset.readerView ?? ""); }
export function scrollFraction(document: Document) {
  const root = document.scrollingElement ?? document.documentElement;
  const maximum = isPaged(document) ? root.scrollWidth - root.clientWidth : root.scrollHeight - root.clientHeight;
  const offset = isPaged(document) ? root.scrollLeft : root.scrollTop;
  return maximum > 0 ? Math.min(1, Math.max(0, offset / maximum)) : 1;
}

export function restoreScroll(document: Document, fraction: number) {
  const root = document.scrollingElement ?? document.documentElement;
  if (isPaged(document)) root.scrollLeft = Math.round((root.scrollWidth - root.clientWidth) * fraction / root.clientWidth) * root.clientWidth;
  else root.scrollTop = (root.scrollHeight - root.clientHeight) * fraction;
}

export function visibleAnchor(document: Document): ReadingAnchor | null {
  const root = document.documentElement, body = document.body.getBoundingClientRect();
  // In a centered reading column the viewport's left edge is outside the text.
  const x = isPaged(document) ? root.clientWidth / 4 : Math.max(32, Math.min(root.clientWidth - 32, body.left + body.width / 3));
  const caret = document.caretPositionFromPoint?.(x, 40);
  const range = document.caretRangeFromPoint?.(x, 40);
  const node = caret?.offsetNode ?? range?.startContainer;
  const offset = caret?.offset ?? range?.startOffset ?? 0;
  if (!node || node.nodeType !== Node.TEXT_NODE || !document.body.contains(node)) return null;
  const point = document.createRange(); point.setStart(node, offset); point.collapse(true);
  return { node, offset, top: point.getBoundingClientRect().top };
}

export function restoreAnchor(document: Document, anchor: ReadingAnchor | null, fraction: number) {
  if (!anchor?.node.isConnected || anchor.node.ownerDocument !== document) { restoreScroll(document, fraction); return; }
  const range = document.createRange(); range.setStart(anchor.node, anchor.offset); range.collapse(true);
  const root = document.scrollingElement ?? document.documentElement;
  const rectangle = range.getBoundingClientRect();
  if (isPaged(document)) root.scrollLeft = Math.floor((rectangle.left + root.scrollLeft) / root.clientWidth) * root.clientWidth;
  else root.scrollTop += rectangle.top - anchor.top;
}
