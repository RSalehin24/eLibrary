"use client";

import { AdminText } from "@/components/admin-language";
import { APIError } from "@/api/http";
import type { BookEditor } from "@/lib/book-editor";

function errorMessage(error: Error) {
  if (error instanceof APIError && error.code === "state_conflict") return "বইটির তথ্য বদলেছে। নতুন তথ্য খুলে তারপর আবার চেষ্টা করুন।";
  if (error instanceof APIError && error.status === 400) return "চিহ্নিত ঘরগুলোর তথ্য ঠিক করে আবার চেষ্টা করুন।";
  return "অনুরোধটি নিশ্চিত করা যায়নি। আবার পাঠানোর আগে নতুন তথ্য খুলে ফলাফল যাচাই করুন।";
}

export function EditorialFeedback({ dirty, notice, error }: Pick<BookEditor, "dirty" | "notice" | "error">) {
  return <>
    {dirty && <p role="status"><AdminText>{"আপনার কিছু পরিবর্তন এখনো সংরক্ষিত হয়নি।"}</AdminText></p>}
    {notice && <p role="status"><AdminText>{notice}</AdminText></p>}
    {error && <div className="field-error" role="alert"><p>{errorMessage(error)}</p>
      <button className="button button-quiet" type="button" onClick={() => {
        if (!dirty || window.confirm("সংরক্ষণ না করা পরিবর্তন বাদ দিয়ে নতুন তথ্য খুলবেন?")) window.location.reload();
      }}><AdminText>{"নতুন তথ্য খুলুন"}</AdminText></button></div>}
  </>;
}
