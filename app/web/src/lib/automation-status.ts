import type { AutomationCreate } from "@/api/types";

export const automationFrequencies: Record<AutomationCreate["frequency"], string> = {
  daily: "প্রতিদিন", weekly: "প্রতি সপ্তাহে", biweekly: "প্রতি দুই সপ্তাহে", monthly: "প্রতি মাসে",
  bimonthly: "প্রতি দুই মাসে", quarterly: "প্রতি তিন মাসে", four_monthly: "প্রতি চার মাসে", half_yearly: "প্রতি ছয় মাসে",
};

export const automationErrors: Readonly<Record<string, string>> = {
  permission_revoked: "যাঁর অনুমতিতে চলার কথা, তাঁর অনুমতি নেই। অনুমোদিত পরিচালক সময়সূচি পরীক্ষা করে সংরক্ষণ করুন।",
  discovery_already_active: "উৎস আবিষ্কারের আরেকটি কাজ চলছিল। এইবারের কাজ শুরু হয়নি।",
  source_configuration_invalid: "উৎসের কনফিগারেশন পরীক্ষা করুন।",
};
