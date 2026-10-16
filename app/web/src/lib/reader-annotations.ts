import type { Highlight } from "@/api/types";

export type TextSelection = { text: string; selector: { start: number; end: number } };

function textNodes(root: Node): Text[] {
  const document = root.ownerDocument!;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
    acceptNode: (node) => node.parentElement?.closest("script,style,noscript,template") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
  });
  const nodes: Text[] = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) nodes.push(node as Text);
  return nodes;
}

export function selectedText(document: Document): TextSelection | null {
  const selection = document.defaultView?.getSelection();
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null;
  const range = selection.getRangeAt(0);
  if (!document.body.contains(range.commonAncestorContainer)) return null;
  const prefix = document.createRange();
  prefix.selectNodeContents(document.body);
  prefix.setEnd(range.startContainer, range.startOffset);
  const start = textNodes(prefix.cloneContents()).reduce((total, node) => total + node.length, 0);
  const text = textNodes(range.cloneContents()).map((node) => node.textContent).join("");
  if (!text.trim() || text.length > 5000) return null;
  return { text, selector: { start, end: start + text.length } };
}

export function selectionRange(document: Document, selector: { start: number; end: number }) {
  const range = document.createRange();
  let offset = 0;
  let started = false;
  for (const node of textNodes(document.body)) {
    if (!started && selector.start < offset + node.length) { range.setStart(node, selector.start - offset); started = true; }
    if (started && selector.end <= offset + node.length) { range.setEnd(node, selector.end - offset); return range; }
    offset += node.length;
  }
  return null;
}

export function applyHighlights(document: Document, annotations: readonly Highlight[]) {
  for (const mark of document.querySelectorAll("mark[data-library-highlight]")) mark.replaceWith(...mark.childNodes);
  document.body.normalize();
  for (const annotation of annotations) {
    if (!annotation.selector) continue;
    const range = selectionRange(document, annotation.selector);
    if (range?.toString().trim() === annotation.text.trim()) markRange(document, range, annotation);
  }
}

function markRange(document: Document, range: Range, annotation: Highlight) {
  const nodes = textNodes(document.body).filter((node) => range.intersectsNode(node));
  for (const node of nodes.reverse()) {
    const segment = document.createRange();
    segment.setStart(node, node === range.startContainer ? range.startOffset : 0);
    segment.setEnd(node, node === range.endContainer ? range.endOffset : node.length);
    if (segment.collapsed) continue;
    const mark = document.createElement("mark");
    mark.dataset.libraryHighlight = annotation.id;
    mark.dataset.color = annotation.color;
    mark.title = annotation.note || "সংরক্ষিত দাগ";
    segment.surroundContents(mark);
  }
}

export function jumpToHighlight(document: Document, annotation: Highlight) {
  if (!annotation.selector) return false;
  return jumpToSelection(document, annotation.selector);
}

export function jumpToSelection(document: Document, selector: { start: number; end: number }) {
  const range = selectionRange(document, selector);
  const element = range?.startContainer.parentElement;
  if (!element) return false;
  element.scrollIntoView({ block: "center" });
  return true;
}
