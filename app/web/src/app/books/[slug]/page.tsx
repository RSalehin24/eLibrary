import type { Metadata } from "next";
import { BookActions } from "@/components/book-actions";
import { getPublicBook } from "@/lib/public-book";
import { canonicalURL } from "@/lib/site";
import { StructuredData } from "@/components/structured-data";
import { BookInformation } from "@/components/book-information";
import { routeSlug } from "@/lib/route-slug";
import { catalogEntityPath } from "@/lib/catalog-entity";
import { Breadcrumbs } from "@/components/breadcrumbs";
import { RelatedEditions } from "@/components/related-editions";
import { BookReadingSummary } from "@/components/book-reading-summary";

type BookParameters = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: BookParameters): Promise<Metadata> {
  const book = await getPublicBook(routeSlug((await params).slug));
  const title = book.seo_title || book.title;
  const description = book.seo_description || book.editorial_description || book.summary || `${book.title} বইয়ের লেখক, সংস্করণ ও পরিচিতি।`;
  return { title, description, alternates: { canonical: `/books/${encodeURIComponent(book.slug)}/` },
    openGraph: { title, description, locale: "bn_BD", type: "website", url: canonicalURL(`/books/${encodeURIComponent(book.slug)}/`),
      ...(book.social_image_url ? { images: [{ url: book.social_image_url, alt: book.title }] } : {}) },
    robots: { index: book.indexable, follow: true },
  };
}

export default async function BookDetailPage({ params }: BookParameters) {
  const book = await getPublicBook(routeSlug((await params).slug));
  const authors = book.contributors.filter((person) => person.role === "author");
  return <>
    <Breadcrumbs entries={[{ name: "পাঠাগার", path: "/catalog/" }, { name: book.title, path: `/books/${encodeURIComponent(book.slug)}/` }]} />
    <BookInformation book={book}>
        <BookActions slug={book.slug} />
    </BookInformation>
    <BookReadingSummary slug={book.slug} />
    <RelatedEditions slug={book.slug} />
    <StructuredData data={{ "@context": "https://schema.org", "@type": "Book", name: book.title,
      url: canonicalURL(`/books/${encodeURIComponent(book.slug)}/`), ...(book.language ? { inLanguage: book.language } : {}),
      ...((book.editorial_description || book.summary) ? { description: book.editorial_description || book.summary } : {}), ...(book.edition ? { bookEdition: book.edition } : {}),
      ...(book.alternative_names.length ? { alternateName: book.alternative_names } : {}),
      ...(book.social_image_url ? { image: book.social_image_url } : {}),
      ...(authors.length ? { author: authors.map((author) => ({ "@type": "Person", name: author.name, url: canonicalURL(catalogEntityPath("contributors", author.slug)) })) } : {}),
    }} />
  </>;
}
