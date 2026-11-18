import { useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import CatalogToolbar from "../components/CatalogToolbar";
import PropertyTable from "../components/PropertyTable";
import { useInfiniteCatalogBooks } from "../hooks/useInfiniteCatalogBooks";
import { usePageTitle } from "../hooks/usePageTitle";
import { formatBookDate } from "../utils/bookPresentation";
import {
  cleanQueryParams,
  filtersFromSearchParams,
  toQueryString,
} from "../utils/query";

const defaultFilters = {
  q: "",
  record_type: "digital",
  created_after: "",
  created_before: "",
  sort: "-book_count",
};

const filterFields = [
  {
    key: "record_type",
    label: "Type",
    type: "select",
    options: [
      { value: "digital", label: "Digital" },
      { value: "manual", label: "Manual" },
      { value: "all", label: "All types" },
    ],
  },
  { key: "created_after", label: "Created after", type: "date" },
  { key: "created_before", label: "Created before", type: "date" },
  {
    key: "sort",
    label: "Sort",
    type: "select",
    options: [
      { value: "-book_count", label: "Most books" },
      { value: "book_count", label: "Fewest books" },
      { value: "name", label: "Name A-Z" },
      { value: "-name", label: "Name Z-A" },
      { value: "catalog_code", label: "Code ascending" },
      { value: "-catalog_code", label: "Code descending" },
      { value: "-created_at", label: "Newest first" },
      { value: "created_at", label: "Oldest first" },
    ],
  },
];

const seriesToolbarFields = filterFields.filter(
  (field) => field.key !== "sort",
);
const seriesSortOptions =
  filterFields.find((field) => field.key === "sort")?.options || [];

export default function SeriesPage() {
  usePageTitle("Series");
  const [searchParams, setSearchParams] = useSearchParams();
  const appliedFilters = useMemo(
    () => filtersFromSearchParams(defaultFilters, searchParams),
    [searchParams],
  );
  const [filters, setFilters] = useState(appliedFilters);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const {
    entries: seriesList,
    totalCount,
    hasMore,
    initialLoading,
    loadingMore,
    refreshing,
    error,
    tableShellRef,
    observeLoadTrigger,
  } = useInfiniteCatalogBooks({
    endpoint: "/catalog/series/",
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

  function buildBooksLink(name) {
    const params = { series: name };
    if (filters.record_type && filters.record_type !== "digital") {
      params.record_type = filters.record_type;
    }
    return `/library${toQueryString(params)}`;
  }

  const resultCount =
    error && !seriesList.length ? "" : `${totalCount}`;
  const showErrorState = Boolean(error && !seriesList.length && !initialLoading);

  return (
    <div className="catalog-page page-stack">
      <header className="catalog-page-header catalog-page-header--with-toolbar catalog-page-header--property-layout">
        <h1>Series</h1>

        <CatalogToolbar
          filters={filters}
          setFilters={setFilters}
          fields={seriesToolbarFields}
          defaultFilters={defaultFilters}
          filtersExpanded={filtersExpanded}
          setFiltersExpanded={setFiltersExpanded}
          onSubmit={applyFilters}
          onReset={resetFilters}
          searchPlaceholder="Search series or codes..."
          resultCount={resultCount}
          resultCountLoading={initialLoading || refreshing}
          sortValue={filters.sort}
          sortOptions={seriesSortOptions}
          onSortChange={(nextSort) => {
            const nextFilters = { ...filters, sort: nextSort };
            setFilters(nextFilters);
            setSearchParams(cleanQueryParams(nextFilters));
          }}
          sortAriaLabel="Sort series"
          searchRowCompact
          searchRowClassName="catalog-search-row--property-compact"
          onSearchClear={clearSearch}
          inline
          bare
          buttonsLoading={initialLoading || refreshing}
          buttonsDisabled={initialLoading || loadingMore || refreshing}
        />
      </header>

      {showErrorState ? (
        <div className="page-state page-state-error">{error}</div>
      ) : (
        <PropertyTable
          headers={[
            "Code",
            "Series",
            "Books",
            "Digital",
            "Manual",
            "Created",
            "Open",
          ]}
          columnKinds={[
            "code",
            "title",
            "stat",
            "stat",
            "stat",
            "date",
            "action",
          ]}
          items={seriesList}
          shellRef={tableShellRef}
          hasMore={hasMore}
          observeLoadTrigger={observeLoadTrigger}
          initialLoading={initialLoading}
          loadingMore={loadingMore}
          refreshing={refreshing}
          shellClassName="catalog-table-shell--incremental"
          renderRow={(series) => (
            <tr key={series.id}>
              <td className="table-code-cell">{series.catalog_code}</td>
              <td>
                <Link
                  to={buildBooksLink(series.name)}
                  className="table-title-link"
                >
                  {series.name}
                </Link>
              </td>
              <td>{series.book_count}</td>
              <td>{series.digital_book_count}</td>
              <td>{series.manual_book_count}</td>
              <td>{formatBookDate(series.created_at)}</td>
              <td className="table-action-cell">
                <Link
                  to={buildBooksLink(series.name)}
                  className="ghost-button table-row-action"
                >
                  Open
                </Link>
              </td>
            </tr>
          )}
          emptyLabel="No series found."
        />
      )}
    </div>
  );
}
