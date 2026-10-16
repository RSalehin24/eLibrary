"use client";

import { AdminText } from "@/components/admin-language";
import { APIError } from "@/api/http";
import type { BookEditorialUpdate, ManagedBookDetail } from "@/api/types";
import { useBookEditor } from "@/lib/book-editor";
import { readBookFormat } from "@/lib/book-format";
import { readEditorialFields } from "@/lib/editorial-fields";
import { BookFormatFields } from "./book-format-fields";
import { BookMetadataFields, EditorialActions } from "./editorial-form-sections";
import { EditorialSEOFields } from "./editorial-metadata-fields";
import { EditorialFeedback } from "./editorial-feedback";
import { BookEpubUpload } from "./book-epub-upload";

function formMetadata(form: HTMLFormElement): Omit<BookEditorialUpdate, "expected_updated_at"> {
  const fields = new FormData(form);
  return { ...readBookFormat(fields), ...readEditorialFields(fields), title: String(fields.get("title")), summary: String(fields.get("summary")) };
}

export function BookEditorialForm({ initialBook }: { initialBook: ManagedBookDetail }) {
  const editor = useBookEditor(initialBook);
  const { book, dirty, save, command, error, pending } = editor;
  const errors = error instanceof APIError ? error.fieldErrors : {};
  return <section className="editorial-workspace">
    <div className="notice"><p><AdminText>{"অবস্থা: "}</AdminText>{book.state === "published" ? "প্রকাশিত" : book.state === "archived" ? "প্রত্যাহৃত" : "খসড়া"}<AdminText>{" · পর্যালোচনা: "}</AdminText><AdminText>{book.editorial_reviewed_at ? "অনুমোদিত" : "প্রয়োজন"}</AdminText></p>
      <p><AdminText>{"তথ্য সম্পাদনার পরে পর্যালোচনা করুন, তারপর প্রকাশ করুন। প্রকাশিত বই সম্পাদনা করলে পর্যালোচনা শেষ হওয়া পর্যন্ত তা জনসাধারণের তালিকা থেকে সরবে।"}</AdminText></p></div>
    <EditorialFeedback dirty={dirty} notice={editor.notice} error={error} />
    <BookEpubUpload editor={editor} />
    <form key={book.updated_at} className="editorial-form" onChange={editor.markDirty} onSubmit={(event) => {
      event.preventDefault(); command.reset(); save.mutate(formMetadata(event.currentTarget));
    }}>
      <BookMetadataFields book={book} pending={pending} errors={errors} />
      <BookFormatFields book={book} pending={pending} errors={errors} />
      <EditorialSEOFields values={book} pending={pending} errors={errors} />
      <button className="button" type="submit" disabled={pending || !dirty}><AdminText>{save.isPending ? "সংরক্ষণ হচ্ছে…" : "পরিবর্তন সংরক্ষণ করুন"}</AdminText></button>
    </form>
    <EditorialActions book={book} pending={pending} dirty={dirty} onCommand={(action) => { save.reset(); command.mutate(action); }} />
  </section>;
}
