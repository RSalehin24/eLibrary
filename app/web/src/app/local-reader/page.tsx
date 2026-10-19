import { LocalBookReader } from "@/components/local-book-reader";

export const dynamic = "force-static";
export const metadata = { title: "নিজের EPUB পড়ুন · Open your EPUB", robots: { index: false, follow: false } };

export default function LocalReaderPage() { return <LocalBookReader />; }
