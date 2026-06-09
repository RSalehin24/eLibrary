import { useEffect, useMemo, useState } from "react";
import { Link, NavLink, useLocation, useSearchParams } from "react-router-dom";
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
      { value: "catalog_code", label: "Code ascending" },
      { value: "-catalog_code", label: "Code descending" },
      { value: "name", label: "Name A-Z" },
      { value: "-name", label: "Name Z-A" },
      { value: "-created_at", label: "Newest first" },
      { value: "created_at", label: "Oldest first" },
    ],
  },
];

const contributorTabs = [
  {
    id: "writers",
    label: "Writers",
    path: "/writers",
    endpoint: "/catalog/writers/",
    role: "author",
    emptyLabel: "No writers found.",
  },
  {
    id: "translators",
    label: "Translators",
    path: "/translators",
    endpoint: "/catalog/translators/",
    role: "translator",
    emptyLabel: "No translators found.",
  },
  {
    id: "editors",
    label: "Editors",
    path: "/editors",
    endpoint: "/catalog/editors/",
    role: "editor",
    emptyLabel: "No editors found.",
  },
  {
    id: "publishers",
    label: "Publishers",
    path: "/publishers",
    endpoint: "/catalog/publishers/",
    role: "publisher",
    emptyLabel: "No publishers found.",
  },
];

function activeTabForPath(pathname) {
  return (
    contributorTabs.find((tab) => tab.path === pathname) || contributorTabs[0]
  );
}

const contributorToolbarFields = filterFields.filter(
  (field) => field.key !== "sort",
);
const contributorSortOptions =
  filterFields.find((field) => field.key === "sort")?.options || [];

export default function WriterPage() {
  const location = useLocation();
  const activeTab = useMemo(
    () => activeTabForPath(location.pathname),
    [location.pathname],
  );
  usePageTitle(activeTab?.label || "Contributors");
  const [searchParams, setSearchParams] = useSearchParams();
  const appliedFilters = useMemo(
    () => filtersFromSearchParams(defaultFilters, searchParams),
    [searchParams],
  );
  const [filters, setFilters] = useState(appliedFilters);
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const {
    entries: contributors,
    totalCount,
    hasMore,
    initialLoading,
    loadingMore,
    refreshing,
    error,
    tableShellRef,
    observeLoadTrigger,
  } = useInfiniteCatalogBooks({
    endpoint: activeTab.endpoint,
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
    const params =
      activeTab.role === "author"
        ? { author: name }
        : { contributor: name, contributor_role: activeTab.role };
    if (filters.record_type && filters.record_type !== "digital") {
      params.record_type = filters.record_type;
    }
    return `/library${toQueryString(params)}`;
  }

  const resultCount =
    error && !contributors.length ? "" : `${totalCount}`;
  const contributorLabel = activeTab.label.toLowerCase();
  const showErrorState = Boolean(error && !contributors.length && !initialLoading);

  return (
    <div className="catalog-page page-stack">
      <header className="contributor-page-header">
        <nav className="contributor-tabs" aria-label="Contributor sections">
          {contributorTabs.map((tab) => (
            <NavLink
              key={tab.id}
              to={tab.path}
              className={({ isActive }) =>
                isActive ? "contributor-tab is-active" : "contributor-tab"
              }
            >
              {tab.label}
            </NavLink>
          ))}
        </nav>

        <div className="catalog-page-header catalog-page-header--with-toolbar catalog-page-header--property-layout contributor-toolbar-row">
          <h1>{activeTab.label}</h1>

          <CatalogToolbar
            filters={filters}
            setFilters={setFilters}
            fields={contributorToolbarFields}
            defaultFilters={defaultFilters}
            filtersExpanded={filtersExpanded}
            setFiltersExpanded={setFiltersExpanded}
            onSubmit={applyFilters}
            onReset={resetFilters}
            searchPlaceholder={`Search ${contributorLabel} or codes...`}
            resultCount={resultCount}
            resultCountLoading={initialLoading || refreshing}
            sortValue={filters.sort}
            sortOptions={contributorSortOptions}
            onSortChange={(nextSort) => {
              const nextFilters = { ...filters, sort: nextSort };
              setFilters(nextFilters);
              setSearchParams(cleanQueryParams(nextFilters));
            }}
            sortAriaLabel={`Sort ${contributorLabel}`}
            searchRowCompact
            searchRowClassName="catalog-search-row--property-compact"
            onSearchClear={clearSearch}
            inline
            bare
            buttonsLoading={initialLoading || refreshing}
            buttonsDisabled={initialLoading || loadingMore || refreshing}
          />
        </div>
      </header>

      {showErrorState ? (
        <div className="page-state page-state-error">{error}</div>
      ) : (
        <PropertyTable
          headers={[
            "Code",
            "Name",
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
          items={contributors}
          shellRef={tableShellRef}
          hasMore={hasMore}
          observeLoadTrigger={observeLoadTrigger}
          initialLoading={initialLoading}
          loadingMore={loadingMore}
          refreshing={refreshing}
          shellClassName="catalog-table-shell--incremental"
          renderRow={(contributor) => (
            <tr key={contributor.id}>
              <td className="table-code-cell">{contributor.catalog_code}</td>
              <td>
                <Link
                  to={buildBooksLink(contributor.name)}
                  className="table-title-link"
                >
                  {contributor.name}
                </Link>
              </td>
              <td>{contributor.book_count}</td>
              <td>{contributor.digital_book_count}</td>
              <td>{contributor.manual_book_count}</td>
              <td>{formatBookDate(contributor.created_at)}</td>
              <td className="table-action-cell">
                <Link
                  to={buildBooksLink(contributor.name)}
                  className="ghost-button table-row-action"
                >
                  Open
                </Link>
              </td>
            </tr>
          )}
          emptyLabel={activeTab.emptyLabel}
        />
      )}
    </div>
  );
}
