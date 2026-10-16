import Link from "next/link";

export default function NotFoundPage() {
  return <section className="empty-state"><h1>পাতাটি পাওয়া যায়নি</h1><p>বইটি প্রকাশিত না-ও হতে পারে, অথবা ঠিকানাটি বদলে গেছে।</p>
    <Link className="button" href="/catalog/">পাঠাগারে ফিরে যান</Link></section>;
}
