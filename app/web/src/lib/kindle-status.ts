import type { KindleOperation } from "../api/types";

export const kindleStates: Record<KindleOperation["state"], string> = {
  queued: "পাঠানোর অপেক্ষায়", running: "পাঠানোর কাজ চলছে", retry_wait: "আবার চেষ্টার অপেক্ষায়", paused: "স্থগিত", cancelled: "বাতিল",
  succeeded: "মেইল সার্ভার গ্রহণ করেছে", failed: "পাঠানো সম্পূর্ণ হয়নি", needs_attention: "ফল নিশ্চিত করা প্রয়োজন",
};
export const recipientStates: Record<KindleOperation["recipients"][number]["outcome"], string> = {
  accepted: "মেইল সার্ভার গ্রহণ করেছে", rejected: "মেইল সার্ভার গ্রহণ করেনি", uncertain: "গ্রহণের ফল নিশ্চিত নয়", not_sent: "পাঠানো হয়নি", pending: "এখনও পাঠানো হয়নি",
};
const errors: Record<string, string> = {
  permission_revoked: "এই বই পাঠানোর অনুমতি বদলেছে।", recipient_removed: "বেছে নেওয়া ঠিকানাটি প্রোফাইলে এখন নেই।",
  asset_changed: "বইয়ের ফাইলটি বদলেছে।", attachment_too_large: "বইয়ের ফাইলটি ইমেইলের আকারসীমা ছাড়িয়েছে।",
  mail_acceptance_unknown: "মেইল গ্রহণের ফল নিশ্চিত নয়। পরীক্ষা না করে আবার পাঠাবেন না।",
  recipient_rejected: "মেইল সার্ভার ঠিকানাটি গ্রহণ করেনি।", message_rejected: "মেইল সার্ভার বইটি গ্রহণ করেনি।",
  mail_connection_unavailable: "মেইল সার্ভারে সংযোগ পাওয়া যায়নি।", sender_configuration_changed: "প্রেরকের ঠিকানা বদলেছে। অনুমোদিত প্রেরকের তালিকা মিলিয়ে নিন।",
};

export function kindleError(code: string) { return Object.hasOwn(errors, code) ? errors[code] : "পাঠানোর কাজটি সম্পূর্ণ হয়নি। ফল ও ঠিকানাগুলো পরীক্ষা করুন।"; }
