import type { AdminLanguage } from "./admin-language";
import { translateSite } from "./site-language";
import { bengaliNumber } from "./site";

const bengaliErrors: Record<string, string> = {
  "This field is required.": "এই তথ্যটি দিন।",
  "This field may not be blank.": "এই ঘরটি খালি রাখা যাবে না।",
  "This field may not be null.": "এই তথ্যটি দিন।",
  "Enter a valid email address.": "সঠিক ইমেইল ঠিকানা দিন।",
  "Enter a valid URL.": "সঠিক ওয়েব ঠিকানা দিন।",
  "A valid integer is required.": "পূর্ণ সংখ্যা দিন।",
  "A valid number is required.": "সঠিক সংখ্যা দিন।",
  "Must be a valid boolean.": "চালু বা বন্ধ বেছে নিন।",
  "Must be a valid UUID.": "সঠিক পরিচয় নম্বর দিন।",
  "Current password is incorrect.": "বর্তমান পাসওয়ার্ডটি সঠিক নয়।",
  "Enter your current password.": "বর্তমান পাসওয়ার্ড দিন।",
  "Enter a new password.": "নতুন পাসওয়ার্ড দিন।",
  "Confirm your new password.": "নতুন পাসওয়ার্ড আবার লিখুন।",
  "The new password fields must match.": "দুই ঘরে একই নতুন পাসওয়ার্ড লিখুন।",
  "The passwords do not match.": "দুই ঘরে একই পাসওয়ার্ড লিখুন।",
  "Choose a different password.": "আগেরটি থেকে আলাদা পাসওয়ার্ড দিন।",
  "This password is too common.": "এই পাসওয়ার্ডটি সহজে অনুমান করা যায়। অন্য পাসওয়ার্ড দিন।",
  "This password is entirely numeric.": "পাসওয়ার্ডে সংখ্যা ছাড়াও অক্ষর দিন।",
  "An account is required to change a password.": "পাসওয়ার্ড বদলাতে অ্যাকাউন্টে প্রবেশ করুন।",
  "An account already uses this email address.": "এই ইমেইল দিয়ে আগে থেকেই একটি অ্যাকাউন্ট আছে।",
  "An entity with this name already exists.": "এই নামে একটি পরিচিতি আছে।",
  "Choose a different edition.": "অন্য সংস্করণ বেছে নিন।",
  "Choose an available book.": "তালিকা থেকে একটি বই বেছে নিন।",
  "Choose the matching book.": "মিল পাওয়া বইটি বেছে নিন।",
  "Inspect the current candidate before linking.": "যুক্ত করার আগে মিল পাওয়া বইয়ের তথ্য দেখুন।",
  "One or more selected books are unavailable.": "বেছে নেওয়া বইগুলোর মধ্যে এক বা একাধিক বই এখন পাওয়া যাচ্ছে না।",
  "One or more selected references are unavailable.": "বেছে নেওয়া পরিচিতিগুলোর মধ্যে এক বা একাধিক এখন পাওয়া যাচ্ছে না।",
  "Only collections contain an ordered book selection.": "শুধু সংগ্রহের বইগুলো ক্রমানুসারে সাজানো যায়।",
  "Publication commands apply to collections.": "এই প্রকাশের নির্দেশটি শুধু সংগ্রহের জন্য প্রযোজ্য।",
  "Choose an image up to 5 MiB.": "সর্বোচ্চ ৫ MiB আকারের ছবি বেছে নিন।",
  "Choose a valid, single-frame PNG, JPEG, or WebP image up to 2048×2048 pixels.": "সর্বোচ্চ ২০৪৮×২০৪৮ পিক্সেলের PNG, JPEG বা WebP ছবি দিন। চলমান ছবি দেওয়া যাবে না।",
  "Upload a valid, readable EPUB archive.": "সঠিক ও খোলা যায় এমন EPUB ফাইল দিন।",
  "Upload an EPUB no larger than 24 MiB.": "সর্বোচ্চ ২৪ MiB আকারের EPUB ফাইল দিন।",
  "EPUB uploads require a digital book record.": "EPUB আপলোড করতে বইয়ের ধরন ডিজিটাল হতে হবে।",
  "Enter one Kindle email per line.": "প্রতি লাইনে একটি Kindle ইমেইল দিন।",
  "Enter a Kindle email ending in @kindle.com.": "@kindle.com দিয়ে শেষ হয় এমন Kindle ইমেইল দিন।",
  "You do not have the Send to Kindle permission.": "আপনার Kindle-এ বই পাঠানোর অনুমতি নেই।",
  "Refresh your profile before saving.": "সংরক্ষণের আগে প্রোফাইলের বর্তমান তথ্য খুলুন।",
  "Code verification failed. Wait before trying again.": "কোডটি যাচাই করা যায়নি। কিছুক্ষণ পরে আবার চেষ্টা করুন।",
  "Two-factor authentication is already enabled.": "দুই ধাপের নিরাপত্তা আগেই চালু আছে।",
  "Two-factor authentication is not enabled.": "দুই ধাপের নিরাপত্তা চালু নেই।",
  "Start two-factor setup before confirming.": "আগে দুই ধাপের নিরাপত্তা চালু করার ধাপ শুরু করুন।",
  "Your administrator requires two-factor authentication.": "পরিচালক আপনার অ্যাকাউন্টে দুই ধাপের নিরাপত্তা বাধ্যতামূলক করেছেন।",
  "Sign out before using a password link.": "পাসওয়ার্ডের লিংক ব্যবহার করতে আগে প্রস্থান করুন।",
  "Invalid reset link.": "পাসওয়ার্ড বদলানোর লিংকটি সঠিক নয়।",
  "Reset token is invalid or expired.": "পাসওয়ার্ড বদলানোর লিংকটি সঠিক নয় অথবা মেয়াদ শেষ হয়েছে।",
  "This password link is invalid or expired.": "পাসওয়ার্ডের লিংকটি সঠিক নয় অথবা মেয়াদ শেষ হয়েছে।",
  "Select at least one account permission.": "অন্তত একটি অনুমতি বেছে নিন।",
  "Read Once and Durable Read permissions are mutually exclusive.": "একবার পড়া ও স্থায়ীভাবে পড়ার অনুমতি একসঙ্গে দেওয়া যাবে না।",
  "This permission is managed through maintenance.": "এই অনুমতি রক্ষণাবেক্ষণ ব্যবস্থা থেকে বদলাতে হবে।",
  "Set a password or send an invite email.": "পাসওয়ার্ড দিন অথবা আমন্ত্রণের ইমেইল পাঠান।",
  "Activate the account before sending an invite email.": "আমন্ত্রণ পাঠানোর আগে অ্যাকাউন্টটি সক্রিয় করুন।",
  "Choose a future first run time.": "প্রথমবার চালানোর জন্য ভবিষ্যতের সময় বেছে নিন।",
  "Choose a valid local time and IANA time zone.": "সঠিক সময় ও সময়ের অঞ্চল বেছে নিন।",
  "This local time is skipped by a daylight saving change. Choose another time.": "ঋতু অনুযায়ী ঘড়ি বদলানোর কারণে এই সময়টি পাওয়া যাবে না। অন্য সময় বেছে নিন।",
  "Configure an allowed canonical book source before processing.": "বই তৈরির আগে অনুমোদিত ওয়েবসাইটের সেটিংস ঠিক করুন।",
  "Configure the source website before processing.": "বই তৈরির আগে ওয়েবসাইটের সেটিংস ঠিক করুন।",
  "Select each source and operation identifier once.": "একই উৎস বা কাজের পরিচয় একাধিকবার বেছে নেবেন না।",
};

export function translateFieldError(language: AdminLanguage, message: string): string {
  if (language === "en") return translateSite(language, message);
  if (Object.hasOwn(bengaliErrors, message)) return bengaliErrors[message];
  const maximum = message.match(/^Ensure this field has no more than (\d+) characters\.$/);
  if (maximum) return `সর্বোচ্চ ${bengaliNumber(Number(maximum[1]))} অক্ষর লিখুন।`;
  const minimum = message.match(/^This password is too short\. It must contain at least (\d+) characters\.$/);
  if (minimum) return `অন্তত ${bengaliNumber(Number(minimum[1]))} অক্ষরের পাসওয়ার্ড দিন।`;
  const length = message.match(/^Ensure this field has at least (\d+) characters\.$/);
  if (length) return `অন্তত ${bengaliNumber(Number(length[1]))} অক্ষর লিখুন।`;
  if (/^The password is too similar to the .+\.$/.test(message)) return "পাসওয়ার্ডের সঙ্গে আপনার ব্যক্তিগত তথ্যের বেশি মিল আছে। অন্য পাসওয়ার্ড দিন।";
  return message;
}
