import type { ReaderSession } from "@/api/types";

type Entry = NonNullable<ReaderSession["navigation"]>[number];
type ContentsNode = Entry & { children: ContentsNode[] };

function contentsTree(session: ReaderSession) {
  const entries = session.navigation?.length ? session.navigation : session.chapters.map((chapter, index) => ({ label: chapter.label, chapter_index: index, fragment: "", depth: 0 }));
  const roots: ContentsNode[] = [], parents: ContentsNode[] = [];
  for (const entry of entries) {
    const node = { ...entry, children: [] };
    while (parents.length > entry.depth) parents.pop();
    (parents.at(-1)?.children ?? roots).push(node);
    parents.push(node);
  }
  return roots;
}

export function ReaderContents({ session, chapter, onNavigate }: { session: ReaderSession; chapter: number; onNavigate: (index: number, fragment?: string) => void }) {
  function items(nodes: ContentsNode[]) {
    return <ol>{nodes.map((node, index) => <li key={index}>
      {node.chapter_index === null ? <span className="reader-contents-heading">{node.label}</span> : <button className="reader-chapter" aria-current={node.chapter_index === chapter && !node.fragment ? "page" : undefined} onClick={() => onNavigate(node.chapter_index!, node.fragment ? `#${encodeURIComponent(node.fragment)}` : undefined)}>{node.label}</button>}
      {node.children.length > 0 && items(node.children)}
    </li>)}</ol>;
  }
  return <div className="reader-contents">{items(contentsTree(session))}</div>;
}
