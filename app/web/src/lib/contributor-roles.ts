import type { BookRelationships } from "@/api/types";

export const contributorRoles: Record<BookRelationships["contributors"][number]["role"], string> = { author: "লেখক", translator: "অনুবাদক", compiler: "সংকলক", editor: "সম্পাদক", illustrator: "অলংকরণ", cover_artist: "প্রচ্ছদশিল্পী", publisher: "প্রকাশক", other: "অন্যান্য" };
