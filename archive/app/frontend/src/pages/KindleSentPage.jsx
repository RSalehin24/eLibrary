import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { sendBookToKindle } from "../api/catalog";
import BookCardGrid from "../components/BookCardGrid";
import CatalogToolbar from "../components/CatalogToolbar";
import EmptyState from "../components/EmptyState";
import { useInfiniteCatalogBooks } from "../hooks/useInfiniteCatalogBooks";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSession } from "../hooks/useSession";
import { useToast } from "../hooks/useToast";
import { useMyBooksAction } from "../features/library/useMyBooksAction";
import { cleanQueryParams, filtersFromSearchParams } from "../utils/query";
import { catalogFetch } from "../api/catalog";

const defaultFilters = {
  q: "",
  author: "",
  series: "",
  category: "",
  record_type: "digital",
  sort: "-sent_at",
  kindle_sent: "mine",
};

const kindleSentFilterFields = [
  {
    key: "sort",
    label: "Sort",
    type: "select",
    options: [
      { value: "-sent_at", label: "Newest send first" },
      { value: "sent_at", label: "Oldest send first" },
      { value: "-created_at", label: "Newest book first" },
      { value: "created_at", label: "Oldest book first" },
      { value: "title", label: "Title A-Z" },
      { value: "-title", label: "Title Z-A" },
    ],
  },
];

const kindleSentSortOptions =
  kindleSentFilterFields.find((field) => field.key === "sort")?.options || [];

export default function KindleSentPage() {
  usePageTitle("Kindle");
  const toast = useToast();
  const { user } = useSession();
  const [sendingBookKindleIds, setSendingBookKindleIds] = useState({});
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

  const kindleSentToolbarFields = useMemo(() => {
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
    updateEntry,
    observeLoadTrigger,
  } = useInfiniteCatalogBooks({
    filters: appliedFilters,
  });

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

  const handleSendToKindle = useCallback(async (book) => {
    if (!book?.slug) return;
    setSendingBookKindleIds((prev) => ({ ...prev, [book.id]: true }));
    try {
      const payload = await sendBookToKindle(book.slug);
      toast.success(payload?.detail || "Sent to Kindle.");
      updateEntry(book.id, {
        has_sent_to_kindle: true,
        user_kindle_sent_at: new Date().toISOString(),
      });
    } catch (err) {
      toast.error(err.message);
    } finally {
      setSendingBookKindleIds((prev) => {
        const next = { ...prev };
        delete next[book.id];
        return next;
      });
    }
  }, [toast, updateEntry]);

  const myBooksAction = useMyBooksAction({ toast, updateEntry });

  const resultCount = error && !books.length ? "" : `${totalCount}`;
  const showErrorState = Boolean(error && !books.length && !initialLoading);

  return (
    <div className="catalog-page page-stack">
      <header className="catalog-page-header catalog-page-header--with-toolbar catalog-page-header--property-layout catalog-page-header--sticky">
        <h1>Kindle</h1>

        <CatalogToolbar
          filters={filters}
          setFilters={setFilters}
          fields={kindleSentToolbarFields}
          defaultFilters={defaultFilters}
          filtersExpanded={filtersExpanded}
          setFiltersExpanded={setFiltersExpanded}
          onSubmit={applyFilters}
          onReset={resetFilters}
          searchPlaceholder="Search by title or book ID..."
          resultCount={resultCount}
          resultCountLoading={initialLoading || refreshing}
          onSearchClear={clearSearch}
          sortValue={filters.sort}
          sortOptions={kindleSentSortOptions}
          onSortChange={(nextSort) => {
            const nextFilters = {
              ...filters,
              sort: nextSort,
            };
            setFilters(nextFilters);
            setSearchParams(cleanQueryParams(nextFilters));
          }}
          sortAriaLabel="Sort kindle sent books"
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
          onMyBooksToggle={myBooksAction.toggleMyBooks}
          myBooksBusyIds={myBooksAction.busyIds}
          onSendToKindle={handleSendToKindle}
          sendingBookKindleIds={sendingBookKindleIds}
          hasKindleEmail={Boolean(user?.kindle_emails?.length)}
        />
      ) : (
        <EmptyState
          title="No books found"
          body="You haven't sent any books to Kindle yet."
        />
      )}
    </div>
  );
}
