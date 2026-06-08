import { useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { catalogFetch } from "../api/catalog";
import BookTable from "../components/BookTable";
import CatalogToolbar from "../components/CatalogToolbar";
import ExportActions from "../components/ExportActions";
import {
  waitForExportUi,
  waitForMinimumLoader,
} from "../features/catalog/exportUiTiming";
import { SavedFilterStrip } from "../features/library/SavedFilterStrip";
import { loadLibraryBooksForExport } from "../features/library/libraryExport";
import {
  LIBRARY_EXPORT_STORAGE_KEY,
  defaultLibraryFilters,
  librarySortOptions,
} from "../features/library/libraryFilters";
import { useDynamicFilterOptions } from "../hooks/useDynamicFilterOptions";
import { useMyBooksAction } from "../features/library/useMyBooksAction";
import { useInfiniteCatalogBooks } from "../hooks/useInfiniteCatalogBooks";
import { usePageTitle } from "../hooks/usePageTitle";
import { useSession } from "../hooks/useSession";
import { useSessionFlag } from "../hooks/useSessionFlag";
import { useToast } from "../hooks/useToast";
import { exportBooksToCsv, exportBooksToPdf } from "../utils/bookExport";
import { getExportBlockState } from "../utils/export";
import {
  clearPendingExport,
  readPendingExport,
  writePendingExport,
} from "../utils/exportSession";
import { cleanQueryParams, filtersFromSearchParams } from "../utils/query";

export default function LibraryPage() {
  usePageTitle("Library");
  const { authenticated } = useSession();
  const toast = useToast();
  const pendingExportRef = useRef(
    readPendingExport(LIBRARY_EXPORT_STORAGE_KEY),
  );
  const resumedPendingExportRef = useRef(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const appliedFilters = useMemo(
    () => filtersFromSearchParams(defaultLibraryFilters, searchParams),
    [searchParams],
  );
  const [filters, setFilters] = useState(appliedFilters);

  const { authors, seriesList, categories } = useDynamicFilterOptions(filters, setFilters);

  const toolbarFields = useMemo(() => {
    return [
      {
        key: "author",
        label: "Contributor",
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
        key: "ownership",
        label: "Ownership",
        type: "select",
        options: [
          { value: "", label: "All books" },
          { value: "mine", label: "My books" }
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
  const [filtersExpanded, setFiltersExpanded] = useSessionFlag(
    "filters-expanded:library",
    false,
  );
  const [savedFilters, setSavedFilters] = useState([]);
  const [savedFilterAction, setSavedFilterAction] = useState("");
  const [downloadState, setDownloadState] = useState(
    () => pendingExportRef.current?.mode || "",
  );
  const {
    books,
    totalCount,
    hasMore,
    initialLoading,
    loadingMore,
    refreshing,
    error,
    updateEntry,
    tableShellRef,
    observeLoadTrigger,
  } = useInfiniteCatalogBooks({
    filters: appliedFilters,
  });
  const myBooksAction = useMyBooksAction({ toast, updateEntry });

  async function loadSavedFilters() {
    if (!authenticated) {
      setSavedFilters([]);
      return;
    }

    try {
      const payload = await catalogFetch("/saved-filters/?target=catalog");
      setSavedFilters(payload);
    } catch (nextError) {
      toast.error(nextError.message);
    }
  }

  useEffect(() => {
    setFilters(appliedFilters);
  }, [appliedFilters]);

  useEffect(() => {
    loadSavedFilters();
  }, [authenticated]);

  useEffect(() => {
    const pendingExport = pendingExportRef.current;
    if (!pendingExport || resumedPendingExportRef.current) {
      return;
    }

    resumedPendingExportRef.current = true;

    async function resumePendingExport() {
      try {
        setDownloadState(pendingExport.mode);
        const startedAt = Date.now();
        await waitForExportUi();

        if (pendingExport.mode === "csv") {
          exportBooksToCsv(
            pendingExport.items,
            pendingExport.filename || "catalog-books.csv",
          );
          toast.success("CSV export started.");
        } else {
          await exportBooksToPdf(
            pendingExport.items,
            pendingExport.title || "Books Export",
          );
          toast.success("PDF export downloaded.");
        }

        await waitForMinimumLoader(startedAt);
      } catch (nextError) {
        toast.error(nextError.message);
      } finally {
        clearPendingExport(LIBRARY_EXPORT_STORAGE_KEY);
        pendingExportRef.current = null;
        setDownloadState("");
      }
    }

    resumePendingExport();
  }, [toast]);

  function applyFilters(event, nextFilters = filters) {
    event.preventDefault();
    setFilters(nextFilters);
    setSearchParams(cleanQueryParams(nextFilters));
  }

  function resetFilters() {
    setFilters(defaultLibraryFilters);
    setSearchParams(cleanQueryParams(defaultLibraryFilters));
  }

  function clearSearch(nextFilters) {
    setFilters(nextFilters);
    setSearchParams(cleanQueryParams(nextFilters));
  }

  function applySavedFilter(savedFilter) {
    if (savedFilterAction) {
      return;
    }
    setSavedFilterAction(`apply:${savedFilter.id}`);
    const nextFilters = {
      ...defaultLibraryFilters,
      ...(savedFilter.params || {}),
    };
    setFilters(nextFilters);
    setSearchParams(cleanQueryParams(nextFilters));
    toast.success(`Applied "${savedFilter.name}".`);
    window.setTimeout(() => setSavedFilterAction(""), 300);
  }

  async function deleteSavedFilter(id) {
    if (savedFilterAction) {
      return;
    }
    try {
      setSavedFilterAction(`delete:${id}`);
      await catalogFetch(`/saved-filters/${id}/`, { method: "DELETE" });
      toast.success("Filter removed.");
      await loadSavedFilters();
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setSavedFilterAction("");
    }
  }

  async function runDownload(mode) {
    setDownloadState(mode);
    try {
      const exportItems = await loadLibraryBooksForExport(appliedFilters);
      const blocked = getExportBlockState({
        items: exportItems,
        loading: initialLoading || refreshing,
        error,
        nounSingular: "book",
        nounPlural: "books",
      });
      if (blocked) {
        toast[blocked.type](blocked.message);
        return;
      }

      const exportRequest = writePendingExport(LIBRARY_EXPORT_STORAGE_KEY, {
        mode,
        items: exportItems,
        title: "Books Export",
        filename: "catalog-books.csv",
      });
      pendingExportRef.current = exportRequest;
      const startedAt = Date.now();
      await waitForExportUi();

      if (mode === "csv") {
        exportBooksToCsv(exportRequest.items, exportRequest.filename);
        toast.success("CSV export started.");
      } else {
        await exportBooksToPdf(exportRequest.items, exportRequest.title);
        toast.success("PDF export downloaded.");
      }

      await waitForMinimumLoader(startedAt);
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      clearPendingExport(LIBRARY_EXPORT_STORAGE_KEY);
      pendingExportRef.current = null;
      setDownloadState("");
    }
  }

  const resultCount = error && !books.length ? "" : `${totalCount}`;
  const exportActions = (
    <ExportActions
      loading={downloadState}
      onExport={runDownload}
      ariaLabel="Export books"
      bare
    />
  );
  const showErrorState = Boolean(error && !books.length && !initialLoading);

  return (
    <div className="catalog-page page-stack">
      <header className="catalog-page-header catalog-page-header--with-toolbar catalog-page-header--property-layout">
        <h1>Books</h1>

        <CatalogToolbar
          filters={filters}
          setFilters={setFilters}
          fields={toolbarFields}
          defaultFilters={defaultLibraryFilters}
          filtersExpanded={filtersExpanded}
          setFiltersExpanded={setFiltersExpanded}
          onSubmit={applyFilters}
          onReset={resetFilters}
          searchPlaceholder="Search books, book IDs, writers, categories..."
          resultCount={resultCount}
          resultCountLoading={initialLoading || refreshing}
          searchActionsExtra={exportActions}
          sortValue={filters.sort}
          sortOptions={librarySortOptions}
          onSortChange={(nextSort) => {
            const nextFilters = {
              ...filters,
              sort: nextSort,
            };
            setFilters(nextFilters);
            setSearchParams(cleanQueryParams(nextFilters));
          }}
          sortAriaLabel="Sort books"
          searchRowCompact
          searchRowClassName="catalog-search-row--property-compact"
          onSearchClear={clearSearch}
          inline
          bare
          buttonsLoading={initialLoading || refreshing}
          buttonsDisabled={initialLoading || loadingMore || refreshing}
        />
      </header>

      <SavedFilterStrip
        onApply={applySavedFilter}
        onDelete={deleteSavedFilter}
        savedFilterAction={savedFilterAction}
        savedFilters={savedFilters}
      />

      {showErrorState ? (
        <div className="page-state page-state-error">{error}</div>
      ) : (
        <BookTable
          books={books}
          emptyLabel="No books found."
          shellClassName="catalog-table-shell--incremental"
          shellRef={tableShellRef}
          hasMore={hasMore}
          observeLoadTrigger={observeLoadTrigger}
          initialLoading={initialLoading}
          loadingMore={loadingMore}
          refreshing={refreshing}
          showMyBooksAction
          onMyBooksToggle={myBooksAction.toggleMyBooks}
          myBooksBusyIds={myBooksAction.busyIds}
          sortValue={appliedFilters.sort}
        />
      )}
    </div>
  );
}
