export function textNodes(root: Node): Text[] {
  const document = root.ownerDocument!;
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT | NodeFilter.SHOW_CDATA_SECTION, {
    acceptNode: node => node.parentElement?.closest("script,style,noscript,template") ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT,
  });
  const nodes: Text[] = [];
  for (let node = walker.nextNode(); node; node = walker.nextNode()) nodes.push(node as Text);
  return nodes;
}

export function selectorFromRange(document: Document, range: Range) {
  const prefix = document.createRange(); prefix.selectNodeContents(document.body); prefix.setEnd(range.startContainer, range.startOffset);
  const start = textNodes(prefix.cloneContents()).reduce((total, node) => total + node.length, 0);
  return { start, end: start + textNodes(range.cloneContents()).reduce((total, node) => total + node.length, 0) };
}

export function selectionRange(document: Document, selector: { start: number; end: number }) {
  const range = document.createRange(); let offset = 0, started = false;
  for (const node of textNodes(document.body)) {
    if (!started && selector.start < offset + node.length) { range.setStart(node, selector.start - offset); started = true; }
    if (started && selector.end <= offset + node.length) { range.setEnd(node, selector.end - offset); return range; }
    offset += node.length;
  }
  return null;
}
