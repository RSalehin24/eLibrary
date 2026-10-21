import Link from "next/link";
import type { ManagedBooks } from "@/api/types";
import { catalogStateLabel } from "@/lib/catalog-state";
import { BookCover } from "./book-cover";
import { Icon } from "./icon";
import { AdminText } from "./admin-language";

export function ManagedBooksTable({ books }: { books: ManagedBooks }) {
  return <div className="admin-data-list"><table className="admin-data-table managed-books-table"><thead><tr><th scope="col"><AdminText>বইয়ের নাম</AdminText></th><th scope="col"><AdminText>বিভাগ</AdminText></th><th scope="col"><AdminText>অবস্থা</AdminText></th><th scope="col"><AdminText>করণীয়</AdminText></th></tr></thead>
    <tbody>{books.entries.map(book => <tr key={book.id}><th scope="row"><div className="admin-book-identity"><BookCover title={book.title} coverUrl={book.cover_url} /><div><Link href={`/manage/books/${encodeURIComponent(book.slug)}/`}>{book.title}</Link><small>{book.contributors.filter(person => person.role === "author").map(person => <Link key={person.id} href={`/manage/books/?${new URLSearchParams({ contributor: person.slug, contributor_role: "author" })}`}>{person.name}</Link>)}</small></div></div></th>
      <td>{book.categories.map(category => <Link key={category.id} href={`/manage/books/?${new URLSearchParams({ category: category.slug })}`}>{category.name}</Link>)}</td>
      <td><span className={`status-label status-${book.state}`}><AdminText>{catalogStateLabel(book.state)}</AdminText></span></td>
      <td className="admin-record-actions"><div className="admin-book-actions"><Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(book.slug)}/`}><Icon name="edit" /><AdminText>সম্পাদনা</AdminText></Link><Link className="button button-quiet" href={`/manage/books/${encodeURIComponent(book.slug)}/#file-tools`}><Icon name="download" /><AdminText>ফাইল</AdminText></Link></div></td>
    </tr>)}</tbody></table></div>;
}
