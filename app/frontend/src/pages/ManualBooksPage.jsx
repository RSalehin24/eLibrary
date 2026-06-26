import { useEffect, useMemo, useRef, useState } from "react";
import BookTable from "../components/BookTable";
import CatalogToolbar from "../components/CatalogToolbar";
import { waitForExportUi, waitForMinimumLoader } from "../features/catalog/exportUiTiming";
import { ManualBookComposer } from "../features/manual-books/ManualBookComposer";
import { ManualBooksToolbarActions } from "../features/manual-books/ManualBooksToolbarActions";
import { createManualBook } from "../features/manual-books/manualBookCreate";
import { loadManualBooksForExport } from "../features/manual-books/manualBookExport";
import {
  MANUAL_BOOKS_EXPORT_STORAGE_KEY,
  defaultManualBookFilters,
  emptyManualBookForm,
  manualBookSortOptions,
} from "../features/manual-books/manualBookFilters";
import { useDynamicFilterOptions } from "../hooks/useDynamicFilterOptions";
import { loadManualBookOptions } from "../features/manual-books/manualBookOptions";
import { useInfiniteCatalogBooks } from "../hooks/useInfiniteCatalogBooks";
import { usePageTitle } from "../hooks/usePageTitle";
import { useToast } from "../hooks/useToast";
import { exportBooksToCsv, exportBooksToPdf } from "../utils/bookExport";
import { getExportBlockState } from "../utils/export";
import {
  clearPendingExport,
  readPendingExport,
  writePendingExport,
} from "../utils/exportSession";

export default function ManualBooksPage() {
  usePageTitle("Manual Books");
  const toast = useToast();
  const titleInputRef = useRef(null);
  const pendingExportRef = useRef(readPendingExport(MANUAL_BOOKS_EXPORT_STORAGE_KEY));
  const resumedPendingExportRef = useRef(false);
  const [composerOpen, setComposerOpen] = useState(false);
  const [form, setForm] = useState(emptyManualBookForm);
  const formRef = useRef(form);
  formRef.current = form;
  const [filters, setFilters] = useState(defaultManualBookFilters);
  const [appliedFilters, setAppliedFilters] = useState(defaultManualBookFilters);

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
  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [contributorOptions, setContributorOptions] = useState([]);
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [seriesOptions, setSeriesOptions] = useState([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [downloadState, setDownloadState] = useState(
    () => pendingExportRef.current?.mode || "",
  );
  const [highlightedBookId, setHighlightedBookId] = useState("");
  const {
    entries: manualBooks,
    totalCount,
    hasMore,
    initialLoading,
    loadingMore,
    refreshing,
    error,
    reload,
    prependEntry,
    tableShellRef,
    observeLoadTrigger,
  } = useInfiniteCatalogBooks({
    endpoint: "/catalog/manual-books/",
    filters: appliedFilters,
  });

  async function loadOptions() {
    try {
      setLoadingOptions(true);
      const options = await loadManualBookOptions();
      setCategoryOptions(options.categories);
      setContributorOptions(options.contributors);
      setSeriesOptions(options.series);
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setLoadingOptions(false);
    }
  }

  useEffect(() => {
    loadOptions();
  }, []);

  useEffect(() => {
    if (!composerOpen) {
      return;
    }
    titleInputRef.current?.focus();
  }, [composerOpen]);

  useEffect(() => {
    if (!highlightedBookId) {
      return undefined;
    }

    const timer = window.setTimeout(() => setHighlightedBookId(""), 2600);
    return () => window.clearTimeout(timer);
  }, [highlightedBookId]);

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
            pendingExport.filename || "manual-books.csv",
          );
          toast.success("CSV export started.");
        } else {
          await exportBooksToPdf(
            pendingExport.items,
            pendingExport.title || "Physical Books' List Export",
          );
          toast.success("PDF export downloaded.");
        }

        await waitForMinimumLoader(startedAt);
      } catch (nextError) {
        toast.error(nextError.message);
      } finally {
        clearPendingExport(MANUAL_BOOKS_EXPORT_STORAGE_KEY);
        pendingExportRef.current = null;
        setDownloadState("");
      }
    }

    resumePendingExport();
  }, [toast]);

  function hasManualBookFormInput(currentForm) {
    return (
      currentForm.title.trim() !== "" ||
      currentForm.summary.trim() !== "" ||
      currentForm.writers.length > 0 ||
      currentForm.translators.length > 0 ||
      currentForm.editors.length > 0 ||
      currentForm.categories.length > 0 ||
      currentForm.series.length > 0 ||
      currentForm.publisher.trim() !== "" ||
      currentForm.price !== "" ||
      currentForm.binding !== "" ||
      currentForm.is_compilation !== false
    );
  }

  async function handleCreate(event) {
    event.preventDefault();
    try {
      setSubmitting(true);
      // Wait for any pending blur/state updates to propagate
      await new Promise((resolve) => setTimeout(resolve, 50));
      const currentForm = formRef.current;

      const payload = await createManualBook(currentForm);
      prependEntry(payload);
      setHighlightedBookId(payload.id);
      setForm(emptyManualBookForm);
      setComposerOpen(true);
      titleInputRef.current?.focus();
      toast.success(
        `Added ${payload.catalog_code}. Ready for the next manual book.`,
      );
      loadOptions();
      void reload({ preserveRows: true });
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDone() {
    try {
      setSubmitting(true);
      // Wait for any pending blur/state updates to propagate
      await new Promise((resolve) => setTimeout(resolve, 50));
      const currentForm = formRef.current;

      if (hasManualBookFormInput(currentForm)) {
        const payload = await createManualBook(currentForm);
        prependEntry(payload);
        setHighlightedBookId(payload.id);
        setForm(emptyManualBookForm);
        setComposerOpen(false);
        toast.success(
          `Added ${payload.catalog_code}.`,
        );
        loadOptions();
        await reload();
      } else {
        setComposerOpen(false);
        await reload();
      }
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setSubmitting(false);
    }
  }

  function applyListFilters(event, nextFilters = filters) {
    event.preventDefault();
    setFilters(nextFilters);
    setAppliedFilters(nextFilters);
  }

  function resetListFilters() {
    setFilters(defaultManualBookFilters);
    setAppliedFilters(defaultManualBookFilters);
  }

  function clearSearch(nextFilters) {
    setFilters(nextFilters);
    setAppliedFilters(nextFilters);
  }

  async function runDownload(mode) {
    setDownloadState(mode);
    try {
      const exportItems = await loadManualBooksForExport(appliedFilters);
      const blocked = getExportBlockState({
        items: exportItems,
        loading: initialLoading || refreshing,
        error,
        nounSingular: "manual book",
        nounPlural: "manual books",
      });
      if (blocked) {
        toast[blocked.type](blocked.message);
        return;
      }

      const exportRequest = writePendingExport(MANUAL_BOOKS_EXPORT_STORAGE_KEY, {
        mode,
        items: exportItems,
        title: "Physical Books' List Export",
        filename: "manual-books.csv",
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
      clearPendingExport(MANUAL_BOOKS_EXPORT_STORAGE_KEY);
      pendingExportRef.current = null;
      setDownloadState("");
    }
  }

  const resultCount =
    error && !manualBooks.length ? "" : `${totalCount}`;
  const showErrorState = Boolean(error && !manualBooks.length && !initialLoading);
  const headerActions = (
    <ManualBooksToolbarActions
      composerOpen={composerOpen}
      downloadState={downloadState}
      onExport={runDownload}
      onToggleComposer={async () => {
        if (composerOpen) {
          await handleDone();
        } else {
          setComposerOpen(true);
        }
      }}
    />
  );

  return (
    <div className="catalog-page page-stack">
      <header className="catalog-page-header catalog-page-header--with-toolbar catalog-page-header--property-layout">
        <h1>Physical Books' List</h1>

        <CatalogToolbar
          filters={filters}
          setFilters={setFilters}
          fields={toolbarFields}
          defaultFilters={defaultManualBookFilters}
          filtersExpanded={filtersExpanded}
          setFiltersExpanded={setFiltersExpanded}
          onSubmit={applyListFilters}
          onReset={resetListFilters}
          searchPlaceholder="Search manual books, book IDs, writers..."
          resultCount={resultCount}
          resultCountLoading={initialLoading || refreshing}
          searchActionsExtra={headerActions}
          sortValue={filters.sort}
          sortOptions={manualBookSortOptions}
          onSortChange={(nextSort) => {
            const nextFilters = { ...filters, sort: nextSort };
            setFilters(nextFilters);
            setAppliedFilters(nextFilters);
          }}
          sortAriaLabel="Sort manual books"
          searchRowCompact
          searchRowClassName="catalog-search-row--property-compact"
          onSearchClear={clearSearch}
          inline
          bare
          buttonsLoading={initialLoading || refreshing}
          buttonsDisabled={initialLoading || loadingMore || refreshing}
        />
      </header>

      {composerOpen ? (
        <ManualBookComposer
          categoryOptions={categoryOptions}
          contributorOptions={contributorOptions}
          seriesOptions={seriesOptions}
          form={form}
          loadingOptions={loadingOptions}
          onClose={handleDone}
          onSubmit={handleCreate}
          setForm={setForm}
          submitting={submitting}
          titleInputRef={titleInputRef}
        />
      ) : null}

      {showErrorState ? (
        <div className="page-state page-state-error">{error}</div>
      ) : (
        <BookTable
          books={manualBooks}
          emptyLabel="No manual books found."
          linkFilters={{ record_type: "manual" }}
          highlightedBookId={highlightedBookId}
          shellClassName="catalog-table-shell--incremental"
          shellRef={tableShellRef}
          hasMore={hasMore}
          observeLoadTrigger={observeLoadTrigger}
          initialLoading={initialLoading}
          loadingMore={loadingMore}
          refreshing={refreshing}
        />
      )}
    </div>
  );
}
