export type ContentsEntry = { label: string; chapter_index: number | null; fragment: string; depth: number };
export type ContentsNode = ContentsEntry & { children: ContentsNode[] };

export function contentsTree(entries: readonly ContentsEntry[]) {
  const roots: ContentsNode[] = [], parents: ContentsNode[] = [];
  for (const entry of entries) {
    const node = { ...entry, children: [] };
    while (parents.length > entry.depth) parents.pop();
    (parents.at(-1)?.children ?? roots).push(node);
    parents.push(node);
  }
  return roots;
}

export function contentsIncludeChapter(node: ContentsNode, chapter: number): boolean {
  return node.chapter_index === chapter || node.children.some(child => contentsIncludeChapter(child, chapter));
}
