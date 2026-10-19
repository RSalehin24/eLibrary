import { catalogFilterMessages } from "./catalog-filter-messages";
import { physicalBookMessages } from "./physical-book-messages";
import { kindleHistoryMessages } from "./kindle-history-messages";
import { sitePublicMessages } from "./site-public-messages";
import { siteAccountMessages } from "./site-account-messages";
import { siteReaderMessages } from "./site-reader-messages";
import { localReaderMessages } from "./local-reader-messages";

export const siteEnglishMessages: Readonly<Record<string, string>> = { "দাগ": "Highlights", "নোট": "Notes", "উদ্ধৃতি": "Quotes", "নোট খুঁজুন": "Search notes", "রং": "Color", "সব রং": "All colors", "হলুদ": "Yellow", "সবুজ": "Green", "নীল": "Blue", "গোলাপি": "Pink", "লেখার নিচে দাগ": "Underline", ...sitePublicMessages, ...siteAccountMessages, ...siteReaderMessages, ...catalogFilterMessages, ...physicalBookMessages, ...kindleHistoryMessages, ...localReaderMessages };
