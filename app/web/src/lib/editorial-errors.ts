import { APIError } from "../api/http";

const sourceProblems: Readonly<Record<string, string>> = {
  "Regenerate the source book to verify its complete text and files.": "বইয়ের সম্পূর্ণ লেখা ও ফাইল স্বয়ংক্রিয়ভাবে যাচাই করতে বইটি আবার তৈরি করুন।",
  "Finish or resolve the source operation before publication.": "বইটি প্রসেস হচ্ছে বা আগের কাজে সমস্যা রয়েছে। প্রসেসিংয়ের অবস্থা দেখুন।",
  "Prepare the source book's HTML and EPUB before publication.": "প্রকাশের জন্য HTML ও EPUB প্রস্তুত থাকতে হবে। প্রসেসিংয়ের অবস্থা দেখুন।",
  "Prepare the source book's reader resources before publication.": "রিডারের ফাইল প্রস্তুত হলে বইটি প্রকাশিত হবে। প্রসেসিংয়ের অবস্থা দেখুন।",
};

export function editorialErrorMessage(error: Error): string {
  if (error instanceof APIError && error.code === "state_conflict") {
    return Object.hasOwn(sourceProblems, error.detail) ? sourceProblems[error.detail] : "বইটির তথ্য বদলেছে। নতুন তথ্য খুলে তারপর আবার চেষ্টা করুন।";
  }
  if (error instanceof APIError && error.status === 400) return "চিহ্নিত ঘরগুলোর তথ্য ঠিক করে আবার চেষ্টা করুন।";
  return "অনুরোধটি নিশ্চিত করা যায়নি। আবার পাঠানোর আগে নতুন তথ্য খুলে ফলাফল যাচাই করুন।";
}
