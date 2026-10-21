import { LocalBookReader } from "@/components/local-book-reader";

export const dynamic = "force-static";
export const metadata = { title: "নিজের EPUB পড়ুন", other: { "library:ui-title": "নিজের EPUB পড়ুন" }, robots: { index: false, follow: false } };

export default function LocalReaderPage() { return <LocalBookReader />; }
