import { parseCfi, splitCfi, unescapeCfi, matchesCfiText, type CfiPoint } from "./reader-cfi-parser";
import { selectorFromRange } from "./reader-text";

type Boundary = { node: Node; offset: number };

function textBoundary(element: Element, point: { slot: number; offset: number }): Boundary | null {
  let slot = 0, offset = point.offset;
  for (const node of element.childNodes) {
    if (node.nodeType === 1) { slot++; continue; }
    if (slot !== point.slot || ![3, 4].includes(node.nodeType)) continue;
    if (offset <= (node.textContent?.length ?? 0)) return { node, offset };
    offset -= node.textContent?.length ?? 0;
  }
  return null;
}

function assertedBoundary(boundary: Boundary, assertion?: string) {
  if (!assertion) return boundary;
  return matchesCfiText(boundary.node.textContent ?? "", boundary.offset, assertion) ? boundary : null;
}

function pointBoundary(document: Document, point: CfiPoint): Boundary | null {
  let element: Element = document.documentElement;
  for (const [index, step] of point.steps.entries()) {
    if (step.number % 2) return index === point.steps.length - 1 ? terminalText(element, point) : null;
    const child = element.children.item(step.number / 2 - 1);
    if (!child) return null;
    element = child;
    const identifier = step.assertion && splitCfi(step.assertion, ";")?.[0];
    if (identifier && element.id !== unescapeCfi(identifier)) return null;
  }
  return point.offset === 0 ? { node: element, offset: 0 } : null;
}

function terminalText(element: Element, point: CfiPoint) {
  const boundary = textBoundary(element, { slot: (point.steps.at(-1)!.number - 1) / 2, offset: point.offset });
  return boundary && assertedBoundary(boundary, point.assertion);
}

export function cfiRange(document: Document, value: string) {
  const parsed = parseCfi(value);
  if (!parsed || parsed.start.spatial || parsed.start.temporal !== undefined || parsed.end?.spatial || parsed.end?.temporal !== undefined) return null;
  const start = pointBoundary(document, parsed.start), end = parsed.end ? pointBoundary(document, parsed.end) : start;
  if (!start || !end || !document.body.contains(start.node) || !document.body.contains(end.node)) return null;
  if ([start, end].some(boundary => (boundary.node.nodeType === 1 ? boundary.node as Element : boundary.node.parentElement)?.closest("script,style,noscript,template"))) return null;
  const range = document.createRange(); range.setStart(start.node, start.offset); range.setEnd(end.node, end.offset);
  if (parsed.end && range.collapsed) return null;
  return range;
}

export function cfiMediaTarget(document: Document, value: string) {
  const parsed = parseCfi(value), point = parsed?.start;
  if (!point || !point.spatial && point.temporal === undefined) return null;
  const start = pointBoundary(document, point), end = parsed?.end && pointBoundary(document, parsed.end);
  if (!start || start.node.nodeType !== 1 || !document.body.contains(start.node) || parsed?.end && (!end || end.node !== start.node)) return null;
  const element = start.node as HTMLImageElement | HTMLMediaElement;
  if (point.spatial && !["img", "video"].includes(element.localName)) return null;
  if (point.temporal !== undefined && !["audio", "video"].includes(element.localName)) return null;
  if (parsed?.end && (Boolean(point.spatial) !== Boolean(parsed.end.spatial) || (point.temporal === undefined) !== (parsed.end.temporal === undefined) || (parsed.end.temporal ?? 0) < (point.temporal ?? 0))) return null;
  return { element, spatial: point.spatial, temporal: point.temporal };
}

export function cfiSelection(document: Document, value: string) {
  const range = cfiRange(document, value);
  return range && !range.collapsed ? selectorFromRange(document, range) : null;
}
