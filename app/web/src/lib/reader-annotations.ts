import type { Highlight } from "@/api/types";
import { isPaged } from "./reader-document";
import { textNodes, selectionRange, selectorFromRange } from "./reader-text";
import { cfiSelection } from "./reader-cfi";
export { selectionRange } from "./reader-text";

export type TextSelection = { text: string; selector: { start: number; end: number } };

function currentSelection(document: Document): TextSelection | null {
  const selection = document.defaultView?.getSelection();
  if (!selection || selection.isCollapsed || selection.rangeCount === 0) return null;
  const range = selection.getRangeAt(0);
  if (!document.body.contains(range.commonAncestorContainer)) return null;
  const text = textNodes(range.cloneContents()).map((node) => node.textContent).join("");
  return { text, selector: selectorFromRange(document, range) };
}

export function selectedText(document: Document): TextSelection | null {
  const selection = currentSelection(document);
  return selection?.text.trim() && selection.text.length <= 5000 ? selection : null;
}

export function applyHighlights(document: Document, annotations: readonly Highlight[]) {
  const selection = currentSelection(document);
  for (const mark of document.querySelectorAll("mark[data-library-highlight]")) mark.replaceWith(...mark.childNodes);
  document.body.normalize();
  const located = annotations.map(annotation => ({ ...annotation, selector: annotation.selector ?? (annotation.legacy_cfi ? cfiSelection(document, annotation.legacy_cfi) : null) }));
  const selectors = new Map<string, { start: number; end: number }>();
  for (const annotation of located) {
    if (!annotation.selector) continue;
    const range = selectionRange(document, annotation.selector);
    if (range?.toString().trim() === annotation.text.trim()) { selectors.set(annotation.id, annotation.selector); markRange(document, range, annotation); }
  }
  if (selection) restoreSelection(document, selection);
  return selectors;
}

function restoreSelection(document: Document, previous: TextSelection) {
  const range = selectionRange(document, previous.selector);
  if (!range || range.toString() !== previous.text) return;
  const selection = document.getSelection();
  selection?.removeAllRanges(); selection?.addRange(range);
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
  const range = selectionRange(document, annotation.selector);
  return range ? range.toString().trim() === annotation.text.trim() && jumpToRange(document, range) : false;
}

export function jumpToSelection(document: Document, selector: { start: number; end: number }) {
  const range = selectionRange(document, selector);
  return range ? jumpToRange(document, range) : false;
}

export function jumpToRange(document: Document, range: Range) {
  const element = range.startContainer.nodeType === 1 ? range.startContainer as Element : range.startContainer.parentElement;
  if (!element) return false;
  const rectangle = range.getClientRects()[0] ?? (range.startContainer.nodeType === 1 ? element.getBoundingClientRect() : null);
  if (!rectangle || rectangle.width === 0 && rectangle.height === 0) return false;
  const root = document.scrollingElement ?? document.documentElement;
  if (isPaged(document)) root.scrollLeft = Math.floor((rectangle.left + root.scrollLeft) / root.clientWidth) * root.clientWidth;
  else root.scrollTop += rectangle.top - root.clientHeight / 3;
  const selection = document.getSelection();
  if (!range.collapsed) { selection?.removeAllRanges(); selection?.addRange(range); }
  return true;
}
