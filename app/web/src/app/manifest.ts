import type { MetadataRoute } from "next";
import { siteName } from "@/lib/site";

export default function manifest(): MetadataRoute.Manifest {
  return { id: "/", name: siteName, short_name: "পাঠাগার", description: "বিশ্বজুড়ে বাংলা পাঠকের ব্যক্তিগত পাঠাগার", lang: "bn", start_url: "/", scope: "/", display: "standalone", theme_color: "#173e35", background_color: "#fbfaf6",
    icons: [{ src: "/icons/book-192-v2.png", sizes: "192x192", type: "image/png", purpose: "any" }, { src: "/icons/book-512-v2.png", sizes: "512x512", type: "image/png", purpose: "any" }, { src: "/icons/book-512-v2.png", sizes: "512x512", type: "image/png", purpose: "maskable" }],
    screenshots: [{ src: "/install/phone-17c005626e37.png", sizes: "390x844", type: "image/png", form_factor: "narrow", label: "ফোনে বাংলা পাঠাগার" }, { src: "/install/desktop-cbe8702ffe66.png", sizes: "1280x720", type: "image/png", form_factor: "wide", label: "কম্পিউটারে বাংলা পাঠাগার" }],
    shortcuts: [{ name: "বই খুঁজুন", url: "/catalog/", description: "বাংলা বইয়ের পরিচিতি খুঁজুন" }, { name: "আমার বই", url: "/my-books/", description: "নিজের পাঠাগার খুলুন" }],
  };
}
