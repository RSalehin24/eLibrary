import { useId, useState } from "react";
import type { ReaderSession } from "@/api/types";
import { contentsTree, contentsIncludeChapter, type ContentsEntry, type ContentsNode } from "@/lib/reader-contents";
import { useSiteLanguage } from "./site-language";

type Navigation = { chapter: number; onNavigate: (index: number, fragment?: string) => void };

function ContentsItem({ node, navigation }: { node: ContentsNode; navigation: Navigation }) {
  const [expanded, setExpanded] = useState(() => contentsIncludeChapter(node, navigation.chapter));
  const identifier = useId(), { t } = useSiteLanguage();
  return <li><div className="reader-contents-row">
    {node.children.length > 0 && <button type="button" className="button button-quiet reader-contents-toggle" aria-expanded={expanded} aria-controls={identifier} aria-label={`${t(expanded ? "সূচির অংশ বন্ধ করুন" : "সূচির অংশ খুলুন")}: ${node.label}`} onClick={() => setExpanded(value => !value)}><span aria-hidden="true">{expanded ? "−" : "+"}</span></button>}
    {node.chapter_index === null ? <span className="reader-contents-heading">{node.label}</span> : <button className="reader-chapter" aria-current={node.chapter_index === navigation.chapter && !node.fragment ? "page" : undefined} onClick={() => navigation.onNavigate(node.chapter_index!, node.fragment ? `#${encodeURIComponent(node.fragment)}` : undefined)}>{node.label}</button>}
  </div>{node.children.length > 0 && <div id={identifier} hidden={!expanded}><ContentsTree nodes={node.children} navigation={navigation} /></div>}</li>;
}

function ContentsTree({ nodes, navigation }: { nodes: ContentsNode[]; navigation: Navigation }) {
  return <ol>{nodes.map((node, index) => <ContentsItem key={index} node={node} navigation={navigation} />)}</ol>;
}

export function ContentsList({ entries, chapter, onNavigate }: { entries: readonly ContentsEntry[] } & Navigation) {
  return <div className="reader-contents"><ContentsTree key={chapter} nodes={contentsTree(entries)} navigation={{ chapter, onNavigate }} /></div>;
}

export function ReaderContents({ session, chapter, onNavigate }: { session: ReaderSession } & Navigation) {
  const entries = session.navigation?.length ? session.navigation : session.chapters.map((entry, index) => ({ label: entry.label, chapter_index: index, fragment: "", depth: 0 }));
  return <ContentsList key={session.id} entries={entries} chapter={chapter} onNavigate={onNavigate} />;
}
