import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { removeBookFromMyBooks } from "../api/catalog";
import BookCardGrid from "../components/BookCardGrid";
import CatalogToolbar from "../components/CatalogToolbar";
import EmptyState from "../components/EmptyState";
import { useInfiniteCatalogBooks } from "../hooks/useInfiniteCatalogBooks";
import { useAsyncAction } from "../hooks/useAsyncAction";
import { usePageTitle } from "../hooks/usePageTitle";
import { useToast } from "../hooks/useToast";
import { cleanQueryParams, filtersFromSearchParams } from "../utils/query";
import { catalogFetch } from "../api/catalog";

const defaultFilters = {
  q: "",
  author: "",
  series: "",
  category: "",
  record_type: "digital",
  sort: "-requested_at",
  ownership: "mine",
};

const createdBookFilterFields = [
  {
    key: "sort",
    label: "Sort",
    type: "select",
    options: [
      { value: "-requested_at", label: "Newest request first" },
      { value: "requested_at", label: "Oldest request first" },
      { value: "-created_at", label: "Newest book first" },
      { value: "created_at", label: "Oldest book first" },
      { value: "title", label: "Title A-Z" },
      { value: "-title", label: "Title Z-A" },
    ],
  },
];

const createdBookToolbarFields = createdBookFilterFields.filter(
  (field) => field.key !== "sort",
);
const createdBookSortOptions =
  createdBookFilterFields.find((field) => field.key === "sort")?.options || [];

export default function CreatedBooksPage() {
  usePageTitle("My Books");
  const toast = useToast();
  const [searchParams, setSearchParams] = useSearchParams();
  const appliedFilters = useMemo(
    () => filtersFromSearchParams(defaultFilters, searchParams),
    [searchParams],
  );
  const [filters, setFilters] = useState(appliedFilters);
  const [filtersExpanded, setFiltersExpanded] = useState(false);

  const [authors, setAuthors] = useState([]);
  const [seriesList, setSeriesList] = useState([]);
  const [categories, setCategories] = useState([]);

  useEffect(() => {
    async function loadOptions() {
      try {
        const [authorsData, seriesData, categoriesData] = await Promise.all([
          catalogFetch("/catalog/writers/?record_type=all&sort=name"),
          catalogFetch("/catalog/series/?record_type=all&sort=name"),
          catalogFetch("/catalog/categories/?record_type=all&sort=name"),
        ]);
        setAuthors(authorsData.map(item => item.name));
        setSeriesList(seriesData.map(item => item.name));
        setCategories(categoriesData.map(item => item.name));
      } catch (err) {
        console.error("Failed to load filter options:", err);
      }
    }
    loadOptions();
  }, []);

  const createdBookToolbarFields = useMemo(() => {
    return [
      {
        key: "author",
        label: "Author",
        type: "searchable-select",
        options: [
          { value: "", label: "Any" },
          ...authors.map(name => ({ value: name, label: name }))
        ]
      },
      {
        key: "series",
        label: "Series",
        type: "searchable-select",
        options: [
          { value: "", label: "Any" },
          ...seriesList.map(name => ({ value: name, label: name }))
        ]
      },
      {
        key: "category",
        label: "Category",
        type: "searchable-select",
        options: [
          { value: "", label: "Any" },
          ...categories.map(name => ({ value: name, label: name }))
        ]
      },
      {
        key: "record_type",
        label: "Type",
        type: "select",
        options: [
          { value: "digital", label: "Digital" },
          { value: "manual", label: "Manual" },
          { value: "all", label: "All types" }
        ]
      }
    ];
  }, [authors, seriesList, categories]);

  const {
    books,
    totalCount,
    hasMore,
    initialLoading,
    loadingMore,
    refreshing,
    error,
    removeEntry,
    observeLoadTrigger,
  } = useInfiniteCatalogBooks({
    filters: appliedFilters,
  });
  const removeAction = useAsyncAction();

  useEffect(() => {
    setFilters(appliedFilters);
  }, [appliedFilters]);

  function applyFilters(event, nextFilters = filters) {
    event.preventDefault();
    setFilters(nextFilters);
    setSearchParams(cleanQueryParams(nextFilters));
  }

  function resetFilters() {
    setFilters(defaultFilters);
    setSearchParams(cleanQueryParams(defaultFilters));
  }

  function clearSearch(nextFilters) {
    setFilters(nextFilters);
    setSearchParams(cleanQueryParams(nextFilters));
  }

  async function removeFromMyBooks(book) {
    await removeAction
      .run(book.id, async () => {
        await removeBookFromMyBooks(book.slug);
        removeEntry(book.id);
        toast.success("Removed from My Books.");
      })
      .catch((nextError) => toast.error(nextError.message));
  }

  const resultCount = error && !books.length ? "" : `${totalCount}`;
  const showErrorState = Boolean(error && !books.length && !initialLoading);

  return (
    <div className="catalog-page page-stack">
      <header className="catalog-page-header catalog-page-header--with-toolbar catalog-page-header--property-layout catalog-page-header--sticky">
        <h1>My Books</h1>

        <CatalogToolbar
          filters={filters}
          setFilters={setFilters}
          fields={createdBookToolbarFields}
          defaultFilters={defaultFilters}
          filtersExpanded={filtersExpanded}
          setFiltersExpanded={setFiltersExpanded}
          onSubmit={applyFilters}
          onReset={resetFilters}
          searchPlaceholder="Search your books by title or book ID..."
          resultCount={resultCount}
          resultCountLoading={initialLoading || refreshing}
          onSearchClear={clearSearch}
          sortValue={filters.sort}
          sortOptions={createdBookSortOptions}
          onSortChange={(nextSort) => {
            const nextFilters = {
              ...filters,
              sort: nextSort,
            };
            setFilters(nextFilters);
            setSearchParams(cleanQueryParams(nextFilters));
          }}
          sortAriaLabel="Sort my books"
          searchRowCompact
          searchRowClassName="catalog-search-row--property-compact"
          inline
          bare
          buttonsLoading={initialLoading || refreshing}
          buttonsDisabled={initialLoading || loadingMore || refreshing}
        />
      </header>

      {showErrorState ? (
        <div className="page-state page-state-error">{error}</div>
      ) : books.length || initialLoading || refreshing ? (
        <BookCardGrid
          books={books}
          hasMore={hasMore}
          observeLoadTrigger={observeLoadTrigger}
          initialLoading={initialLoading}
          loadingMore={loadingMore}
          refreshing={refreshing}
          onRemoveFromMyBooks={removeFromMyBooks}
          removingBookIds={{ [removeAction.pendingKey]: true }}
        />
      ) : (
        <EmptyState
          title="No books found"
          body="Adjust the search or filters."
        />
      )}
    </div>
  );
}
