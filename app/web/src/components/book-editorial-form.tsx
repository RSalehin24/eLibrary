"use client";

import { catalogStateLabel } from "@/lib/catalog-state";
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
import { BookLifecycleControls } from "./book-lifecycle-controls";
import { ProcessingAssets } from "./processing-assets";

function formMetadata(form: HTMLFormElement): Omit<BookEditorialUpdate, "expected_updated_at"> {
  const fields = new FormData(form);
  return { ...readBookFormat(fields), ...readEditorialFields(fields), title: String(fields.get("title")), summary: String(fields.get("summary")) };
}

export function BookEditorialForm({ initialBook, canProcess = false }: { initialBook: ManagedBookDetail; canProcess?: boolean }) {
  const editor = useBookEditor(initialBook);
  const { book, dirty, save, command, error, pending } = editor;
  const errors = error instanceof APIError ? error.fieldErrors : {};
  return <section className="editorial-workspace">
    <div className="notice"><p><AdminText>{"অবস্থা: "}</AdminText><AdminText>{catalogStateLabel(book.state)}</AdminText></p>
      <p><AdminText>{"সংরক্ষণ করে প্রকাশ করুন। প্রকাশিত বইয়ের পরিবর্তন সংরক্ষণ করলেই দেখা যাবে।"}</AdminText></p></div>
    <EditorialFeedback dirty={dirty} notice={editor.notice} error={error} />
    <div className="editor-toolbar"><button className="button" type="submit" form={`book-edit-${book.id}`} disabled={pending || !dirty}><AdminText>{save.isPending ? "সংরক্ষণ হচ্ছে…" : "পরিবর্তন সংরক্ষণ করুন"}</AdminText></button><EditorialActions book={book} pending={pending} dirty={dirty} onCommand={(action) => { save.reset(); command.mutate(action); }} /></div>
    <BookLifecycleControls editor={editor} />
    {canProcess && book.record_type !== "manual" && <ProcessingAssets slug={book.slug} />}
    <BookEpubUpload editor={editor} />
    <form id={`book-edit-${book.id}`} key={book.updated_at} className="editorial-form" onChange={editor.markDirty} onSubmit={(event) => {
      event.preventDefault(); command.reset(); save.mutate(formMetadata(event.currentTarget));
    }}>
      <BookMetadataFields book={book} pending={pending} errors={errors} />
      <BookFormatFields book={book} pending={pending} errors={errors} />
      <EditorialSEOFields values={book} pending={pending} errors={errors} />
    </form>
  </section>;
}
