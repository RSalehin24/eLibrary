"use client";

import { AdminText, useAdminLanguage } from "@/components/admin-language";
import type { BookEditor } from "@/lib/book-editor";
import { editorialErrorMessage } from "@/lib/editorial-errors";

export function EditorialFeedback({ dirty, notice, error }: Pick<BookEditor, "dirty" | "notice" | "error">) {
  const { t } = useAdminLanguage();
  return <>
    {dirty && <p role="status"><AdminText>{"আপনার কিছু পরিবর্তন এখনো সংরক্ষিত হয়নি।"}</AdminText></p>}
    {notice && <p role="status"><AdminText>{notice}</AdminText></p>}
    {error && <div className="field-error" role="alert"><p><AdminText>{editorialErrorMessage(error)}</AdminText></p>
      <button className="button button-quiet" type="button" onClick={() => {
        if (!dirty || window.confirm(t("সংরক্ষণ না করা পরিবর্তন বাদ দিয়ে নতুন তথ্য খুলবেন?"))) window.location.reload();
      }}><AdminText>{"নতুন তথ্য খুলুন"}</AdminText></button></div>}
  </>;
}
