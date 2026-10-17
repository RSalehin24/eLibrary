
import { AdminText } from "@/components/admin-language";
import type { SourceEntry } from "@/api/types";
import { catalogStateLabel } from "@/lib/catalog-state";
import { BookCover } from "./book-cover";
import { ReaderBookCover } from "./reader-book-cover";

export function SourceSummary({ entry }: { entry: SourceEntry }) {
  const book = entry.book && !entry.book.deleted_at ? entry.book : null;
  return <div className="source-book-overview">{book ? <ReaderBookCover slug={book.slug} title={book.title} author={entry.author_line} /> : <BookCover title={entry.title} author={entry.author_line} />}<div><p className="eyebrow"><AdminText>বইয়ের পরিচিতি</AdminText></p><h1>{book?.title ?? entry.title}</h1><p className="muted">{entry.author_line || <AdminText>লেখকের তথ্য নেই</AdminText>}</p>
    <span className="status-label"><AdminText>{book ? catalogStateLabel(book.state) : "এখনও বই তৈরি হয়নি"}</AdminText></span></div></div>;
}
