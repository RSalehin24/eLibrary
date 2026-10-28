import type { ManagedGrantCreate } from "@/api/types";

export const accountStatuses = { all: "সব হিসাব", active: "সক্রিয়", disabled: "নিষ্ক্রিয়", setup_pending: "প্রবেশের প্রস্তুতি বাকি", totp_required: "দুই ধাপে প্রবেশ আবশ্যক" };
export const accountSorts = { name_asc: "নাম: অ থেকে হ", name_desc: "নাম: হ থেকে অ", email_asc: "ইমেইল: A–Z", email_desc: "ইমেইল: Z–A", status: "সক্রিয় অ্যাকাউন্ট আগে" };
export const accessScopes: Record<ManagedGrantCreate["scope"], string> = {
  "access:manage": "ব্যবহারকারী ও অনুমতি পরিচালনা", "processing:manage": "বই প্রক্রিয়াকরণ পরিচালনা", "source_records:view": "উৎসের রেকর্ড দেখা",
  "metadata:edit": "বইয়ের তথ্য সম্পাদনা", "read:once": "একবার পড়া", "send:kindle": "কিন্ডলে পাঠানো",
  "read:durable": "পড়ার অনুমতি", "preview:html": "প্রিভিউ দেখা", "download:file": "বই ডাউনলোড",
};
export const scopedAccess = new Set<ManagedGrantCreate["scope"]>(["metadata:edit", "read:once", "send:kindle", "read:durable", "preview:html", "download:file"]);
export const targetKinds = { account: "সব বই", book: "একটি বই", category: "একটি বিভাগ", author: "একজন লেখক" };
