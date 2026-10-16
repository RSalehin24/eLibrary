import { notFound } from "next/navigation";
import { publicRequest } from "@/api/server";
import type { BookCollection } from "@/api/types";
import { entityFilters, entityLabels, getPublicEntity, type EntityKind, type EntityPageProps } from "@/lib/catalog-entity";
import { routeSlug } from "@/lib/route-slug";
import { canonicalURL } from "@/lib/site";
import { catalogPageNumber } from "@/lib/route-query";
import { BookCard } from "./book-card";
import { CatalogPagination } from "./catalog-pagination";
import { StructuredData } from "./structured-data";
import { Breadcrumbs } from "./breadcrumbs";

export async function CatalogEntityPage({ kind, ...props }: EntityPageProps & { kind: EntityKind }) {
  const entity = await getPublicEntity(kind, routeSlug((await props.params).slug));
  const page = catalogPageNumber(await props.searchParams);
  const parameters = new URLSearchParams({ [entityFilters[kind]]: entity.slug, page: String(page) });
  const books = await publicRequest<BookCollection>(`catalog/books/?${parameters}`);
  if (page > 1 && !books.entries.length) notFound();
  const pathname = `/${kind}/${encodeURIComponent(entity.slug)}/`;
  return <><Breadcrumbs entries={[{ name: "পাঠাগার", path: "/catalog/" }, { name: entity.name, path: pathname }]} />
    <header className="page-title"><p className="eyebrow">{entityLabels[kind]}</p><h1>{entity.name}</h1>
      {entity.editorial_description && <p className="book-description">{entity.editorial_description}</p>}</header>
    <div className="book-grid">{books.entries.map((book) => <BookCard key={book.id} book={book} />)}</div>
    <CatalogPagination pathname={pathname} page={page} hasMore={books.has_more} />
    {kind === "contributors" && <StructuredData data={{ "@context": "https://schema.org", "@type": "Person", name: entity.name,
      url: canonicalURL(pathname), ...(entity.editorial_description ? { description: entity.editorial_description } : {}),
      ...(entity.alternative_names.length ? { alternateName: entity.alternative_names } : {}) }} />}
    {kind === "collections" && <StructuredData data={{ "@context": "https://schema.org", "@type": "CollectionPage", name: entity.name,
      url: canonicalURL(`${pathname}${page > 1 ? `?page=${page}` : ""}`), description: entity.editorial_description,
      mainEntity: { "@type": "ItemList", itemListElement: books.entries.map((book, index) => ({ "@type": "ListItem",
        position: (page - 1) * 24 + index + 1, item: { "@type": "Book", name: book.title, url: canonicalURL(`/books/${encodeURIComponent(book.slug)}/`) } })) } }} />}
  </>;
}
