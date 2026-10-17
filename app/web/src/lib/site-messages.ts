import { sitePublicMessages } from "./site-public-messages";
import { siteAccountMessages } from "./site-account-messages";
import { siteReaderMessages } from "./site-reader-messages";

export const siteEnglishMessages: Readonly<Record<string, string>> = { ...sitePublicMessages, ...siteAccountMessages, ...siteReaderMessages };
