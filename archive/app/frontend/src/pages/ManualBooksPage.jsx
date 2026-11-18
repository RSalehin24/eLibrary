import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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
import { loadManualBookOptions } from "../features/manual-books/manualBookOptions";
import { useInfiniteCatalogBooks } from "../hooks/useInfiniteCatalogBooks";
import { usePageTitle } from "../hooks/usePageTitle";
import { useToast } from "../hooks/useToast";
import { getContributorNamesByRole } from "../utils/bookPresentation";
import { catalogFetch } from "../api/catalog";
import { exportBooksToCsv, exportBooksToPdf, exportManualBooksToExcel } from "../utils/bookExport";
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
  const [exportRowExpanded, setExportRowExpanded] = useState(false);
  const [groupByExcel, setGroupByExcel] = useState("");
  const [form, setFormState] = useState(emptyManualBookForm);
  const formRef = useRef(form);
  const setForm = useCallback((nextForm) => {
    const value = typeof nextForm === "function" ? nextForm(formRef.current) : nextForm;
    formRef.current = value;
    setFormState(value);
  }, []);
  const [filters, setFilters] = useState(defaultManualBookFilters);
  const [appliedFilters, setAppliedFilters] = useState(defaultManualBookFilters);

  const [filtersExpanded, setFiltersExpanded] = useState(false);
  const [writerOptions, setWriterOptions] = useState([]);
  const [translatorOptions, setTranslatorOptions] = useState([]);
  const [editorOptions, setEditorOptions] = useState([]);
  const [contributorOptions, setContributorOptions] = useState([]);
  const [categoryOptions, setCategoryOptions] = useState([]);
  const [seriesOptions, setSeriesOptions] = useState([]);
  const [publisherOptions, setPublisherOptions] = useState([]);
  const [loadingOptions, setLoadingOptions] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [editingBook, setEditingBook] = useState(null);
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

  const toolbarFields = useMemo(() => {
    return [
      {
        key: "writer",
        label: "Writer",
        type: "searchable-select",
        options: [
          { value: "", label: "Any" },
          ...writerOptions.map(name => ({ value: name, label: name }))
        ]
      },
      {
        key: "translator",
        label: "Translator",
        type: "searchable-select",
        options: [
          { value: "", label: "Any" },
          ...translatorOptions.map(name => ({ value: name, label: name }))
        ]
      },
      {
        key: "editor",
        label: "Editor",
        type: "searchable-select",
        options: [
          { value: "", label: "Any" },
          ...editorOptions.map(name => ({ value: name, label: name }))
        ]
      },
      {
        key: "category",
        label: "Category",
        type: "searchable-select",
        options: [
          { value: "", label: "Any" },
          ...categoryOptions.map(name => ({ value: name, label: name }))
        ]
      },
      {
        key: "publisher",
        label: "Publisher",
        type: "searchable-select",
        options: [
          { value: "", label: "Any" },
          ...publisherOptions.map(name => ({ value: name, label: name }))
        ]
      },
      {
        key: "binding",
        label: "Binding",
        type: "select",
        options: [
          { value: "", label: "Any" },
          { value: "hard_cover", label: "Hardcover" },
          { value: "paper_back", label: "Paperback" }
        ]
      },
    ];
  }, [writerOptions, translatorOptions, editorOptions, categoryOptions, publisherOptions]);

  async function loadOptions() {
    try {
      setLoadingOptions(true);
      const options = await loadManualBookOptions();
      setCategoryOptions(options.categories);
      setContributorOptions(options.contributors);
      setWriterOptions(options.writers);
      setTranslatorOptions(options.translators);
      setEditorOptions(options.editors);
      setSeriesOptions(options.series);
      setPublisherOptions(options.publishers);
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
            pendingExport.groupBy || "",
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
      currentForm.binding !== "hard_cover" ||
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

      if (editingBook) {
        const contributorsInput = [
          ...currentForm.writers.map(name => ({ name, role: "author" })),
          ...currentForm.translators.map(name => ({ name, role: "translator" })),
          ...currentForm.editors.map(name => ({ name, role: "editor" })),
          ...(currentForm.publisher ? [{ name: currentForm.publisher, role: "publisher" }] : [])
        ];

        const body = {
          title: currentForm.title,
          summary: currentForm.summary,
          contributors: contributorsInput,
          categories: currentForm.categories,
          series: currentForm.series,
          is_compilation: currentForm.is_compilation,
          binding: currentForm.binding,
          publisher: currentForm.publisher,
          price: currentForm.price === "" ? null : currentForm.price,
          language: currentForm.language,
        };

        await catalogFetch(`/catalog/books/${editingBook.slug}/metadata/`, {
          method: "PATCH",
          body,
        });

        setForm(emptyManualBookForm);
        setEditingBook(null);
        setComposerOpen(false);
        toast.success("Book updated successfully.");
        loadOptions();
        await reload();
      } else {
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
      }
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setSubmitting(false);
    }
  }

  function handleEditBook(book) {
    setEditingBook(book);

    let bindingValue = "";
    const rawBinding = (book.binding || book.manual_binding || "").toLowerCase().trim().replace(/[\s_-]+/g, "");
    if (rawBinding === "hardcover") {
      bindingValue = "hard_cover";
    } else if (rawBinding === "paperback") {
      bindingValue = "paper_back";
    }

    const priceVal = book.price !== undefined && book.price !== null ? book.price : book.manual_price;

    setForm({
      title: book.title || "",
      summary: book.summary || "",
      writers: getContributorNamesByRole(book, "author"),
      translators: getContributorNamesByRole(book, "translator"),
      editors: getContributorNamesByRole(book, "editor"),
      categories: book.categories || [],
      series: book.series || [],
      is_compilation: book.is_compilation || book.manual_is_compilation || false,
      binding: bindingValue,
      publisher: book.publisher || book.manual_publisher || "",
      price: priceVal ? String(priceVal) : "",
      language: book.language || "bn",
    });
    setComposerOpen(true);
  }

  async function handleDone() {
    try {
      if (editingBook) {
        setEditingBook(null);
        setForm(emptyManualBookForm);
        setComposerOpen(false);
        return;
      }

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
        groupBy: groupByExcel,
      });
      pendingExportRef.current = exportRequest;
      const startedAt = Date.now();
      await waitForExportUi();

      if (mode === "csv") {
        exportBooksToCsv(exportRequest.items, exportRequest.filename);
        toast.success("CSV export started.");
      } else {
        await exportBooksToPdf(exportRequest.items, exportRequest.title, exportRequest.groupBy || "");
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

  async function runExcelDownload(groupBy) {
    setDownloadState("excel");
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
      exportManualBooksToExcel(exportItems, groupBy, "manual-books.xlsx");
      toast.success("Excel export downloaded.");
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setDownloadState("");
    }
  }

  const resultCount =
    error && !manualBooks.length ? "" : `${totalCount}`;
  const showErrorState = Boolean(error && !manualBooks.length && !initialLoading);
  const headerActions = (
    <ManualBooksToolbarActions
      composerOpen={composerOpen}
      exportRowExpanded={exportRowExpanded}
      onToggleExportRow={() => setExportRowExpanded(prev => !prev)}
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
          buttonsDisabled={loadingMore || refreshing}
        />

        {exportRowExpanded ? (
          <div className="manual-books-download-row">
            {/* Grouping Dropdown */}
            <select
              className="catalog-toolbar-select"
              value={groupByExcel}
              onChange={(e) => setGroupByExcel(e.target.value)}
              disabled={downloadState !== ""}
              aria-label="Group Excel by"
              title="Group Excel by"
              style={{ minHeight: 40 }}
            >
              <option value="">No grouping</option>
              <option value="category">Category</option>
              <option value="publisher">Publisher</option>
              <option value="binding">Binding</option>
              <option value="language">Language</option>
              <option value="contributor">Contributor</option>
            </select>

            {/* CSV Export */}
            <button
              type="button"
              className={`toolbar-icon-button export-action-button${downloadState === "csv" ? " is-loading" : ""}`}
              onClick={() => {
                if (downloadState === "") {
                  runDownload("csv");
                }
              }}
              disabled={downloadState !== ""}
              aria-label={downloadState === "csv" ? "CSV export is generating" : "CSV export"}
              title="CSV export"
            >
              <span className="toolbar-icon-button-art">
                {downloadState === "csv" ? <span className="loading-spinner" aria-hidden="true" /> : <CsvIcon />}
              </span>
              <span className="toolbar-icon-button-text">CSV</span>
            </button>

            {/* PDF Export */}
            <button
              type="button"
              className={`toolbar-icon-button export-action-button${downloadState === "pdf" ? " is-loading" : ""}`}
              onClick={() => {
                if (downloadState === "") {
                  runDownload("pdf");
                }
              }}
              disabled={downloadState !== ""}
              aria-label={downloadState === "pdf" ? "PDF export is generating" : "PDF export"}
              title="PDF export"
            >
              <span className="toolbar-icon-button-art">
                {downloadState === "pdf" ? <span className="loading-spinner" aria-hidden="true" /> : <PdfIcon />}
              </span>
              <span className="toolbar-icon-button-text">PDF</span>
            </button>

            {/* Excel Export */}
            <button
              type="button"
              className={`toolbar-icon-button export-action-button${downloadState === "excel" ? " is-loading" : ""}`}
              onClick={() => {
                if (downloadState === "") {
                  runExcelDownload(groupByExcel);
                }
              }}
              disabled={downloadState !== ""}
              aria-label={downloadState === "excel" ? "Excel export is generating" : "Excel export"}
              title="Excel export"
            >
              <span className="toolbar-icon-button-art">
                {downloadState === "excel" ? <span className="loading-spinner" aria-hidden="true" /> : <ExcelIcon />}
              </span>
              <span className="toolbar-icon-button-text">Excel</span>
            </button>
          </div>
        ) : null}
      </header>

      {composerOpen ? (
        <ManualBookComposer
          categoryOptions={categoryOptions}
          contributorOptions={contributorOptions}
          seriesOptions={seriesOptions}
          publisherOptions={publisherOptions}
          form={form}
          loadingOptions={loadingOptions}
          onClose={handleDone}
          onSubmit={handleCreate}
          setForm={setForm}
          submitting={submitting}
          titleInputRef={titleInputRef}
          isEditing={Boolean(editingBook)}
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
          showPublisher={true}
          onEditBook={handleEditBook}
          hideSeries={true}
          hideType={true}
          showTime={true}
          limitContributorRole={true}
        />
      )}
    </div>
  );
}

function ExcelIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" style={{ width: 16, height: 16 }}>
      <path
        d="M7.25 4.75h7.72l4.03 4.03v9.97A2.25 2.25 0 0 1 16.75 21h-9.5A2.25 2.25 0 0 1 5 18.75v-11.5A2.25 2.25 0 0 1 7.25 5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M14.75 4.75v4h4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path
        d="M9 12l2.5 3.5L9 19M15 12l-2.5 3.5L15 19"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function CsvIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" style={{ width: 16, height: 16 }}>
      <path
        d="M7.25 4.75h7.72l4.03 4.03v9.97A2.25 2.25 0 0 1 16.75 21h-9.5A2.25 2.25 0 0 1 5 18.75v-11.5A2.25 2.25 0 0 1 7.25 5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M14.75 4.75v4h4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path d="M8 11.5h8M8 15h8M8 18.5h5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

function PdfIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false" style={{ width: 16, height: 16 }}>
      <path
        d="M7.25 4.75h7.72l4.03 4.03v9.97A2.25 2.25 0 0 1 16.75 21h-9.5A2.25 2.25 0 0 1 5 18.75v-11.5A2.25 2.25 0 0 1 7.25 5Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path d="M14.75 4.75v4h4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
      <path
        d="M8.1 16.7v-4.8h1.56c.92 0 1.54.56 1.54 1.43 0 .9-.62 1.47-1.54 1.47H9.4v1.9M13 16.7v-4.8h1.44c1.44 0 2.33.91 2.33 2.4 0 1.48-.89 2.4-2.33 2.4H13ZM9.4 13.75h.26c.36 0 .57-.19.57-.49 0-.28-.21-.47-.57-.47H9.4ZM14 15.63h.35c.85 0 1.38-.47 1.38-1.33 0-.88-.53-1.35-1.38-1.35H14Z"
        fill="currentColor"
      />
    </svg>
  );
}
