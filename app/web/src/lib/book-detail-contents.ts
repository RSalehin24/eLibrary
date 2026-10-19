export type ContentsBranch = { label: string; children: ContentsBranch[] };

export function bookDetailContents(entries: { label: string; depth: number }[]): ContentsBranch[] {
  const roots: ContentsBranch[] = [], parents: ContentsBranch[] = [];
  for (const entry of entries) {
    const node: ContentsBranch = { label: entry.label, children: [] };
    parents.length = Math.min(parents.length, Math.max(0, Math.min(8, entry.depth)));
    (parents.at(-1)?.children ?? roots).push(node);
    parents.push(node);
  }
  return roots;
}
