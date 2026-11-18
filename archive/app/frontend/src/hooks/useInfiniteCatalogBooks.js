import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { catalogFetch } from "../api/catalog";
import {
  CATALOG_TABLE_BATCH_SIZE,
  normalizeCatalogListPayload,
} from "../utils/catalogBooks";
import { toQueryString } from "../utils/query";

export function useInfiniteCatalogBooks({
  endpoint = "/catalog/books/",
  filters,
  enabled = true,
}) {
  const requestFilters = useMemo(() => {
    const { page, limit, ...rest } = filters || {};
    return rest;
  }, [filters]);
  const requestKey = useMemo(
    () =>
      JSON.stringify(
        Object.entries(requestFilters).sort(([left], [right]) => left.localeCompare(right)),
      ),
    [requestFilters],
  );
  const [tableState, setTableState] = useState({
    entries: [],
    totalCount: 0,
    currentPage: 0,
    hasMore: false,
    loadedOnce: false,
    initialLoading: false,
    loadingMore: false,
    refreshing: false,
    error: "",
  });
  const tableStateRef = useRef(tableState);
  const tableShellRef = useRef(null);
  const observerRef = useRef(null);
  const requestSeqRef = useRef(0);
  const previousEndpointRef = useRef(endpoint);
  const previousRequestKeyRef = useRef(requestKey);

  const commitTableState = useCallback((updater) => {
    setTableState((current) => {
      const next =
        typeof updater === "function" ? updater(current) : updater;
      tableStateRef.current = next;
      return next;
    });
  }, []);

  useEffect(() => {
    tableStateRef.current = tableState;
  }, [tableState]);

  const loadPage = useCallback(
    async ({
      page = 1,
      limit = CATALOG_TABLE_BATCH_SIZE,
      append = false,
      preserveRows = false,
      resetState = false,
    } = {}) => {
      const requestSeq = requestSeqRef.current + 1;
      requestSeqRef.current = requestSeq;

      commitTableState((current) => {
        const keepExistingRows =
          append || preserveRows || (!resetState && current.loadedOnce);

        return {
          ...current,
          currentPage: resetState && !append ? 0 : current.currentPage,
          hasMore: resetState && !append ? false : current.hasMore,
          initialLoading:
            !append && !preserveRows && (!current.loadedOnce || resetState),
          loadingMore: append,
          refreshing:
            !append && !resetState && (preserveRows || current.loadedOnce),
          error: "",
          entries: keepExistingRows ? current.entries : [],
          totalCount: keepExistingRows ? current.totalCount : 0,
        };
      });

      try {
        const payload = await catalogFetch(
          `${endpoint}${toQueryString({
            ...requestFilters,
            page: String(page),
            limit: String(limit),
          })}`,
        );
        if (requestSeqRef.current !== requestSeq) {
          return null;
        }

        const normalized = normalizeCatalogListPayload(payload);
        const nextPage = Number(normalized.pagination.page) || page;

        commitTableState((current) => ({
          entries: append
            ? [...current.entries, ...normalized.entries]
            : normalized.entries,
          totalCount: Number(normalized.pagination.total_count) || 0,
          currentPage: nextPage,
          hasMore: Boolean(normalized.pagination.has_next),
          loadedOnce: true,
          initialLoading: false,
          loadingMore: false,
          refreshing: false,
          error: "",
        }));

        return normalized;
      } catch (nextError) {
        if (requestSeqRef.current !== requestSeq) {
          return null;
        }

        commitTableState((current) => ({
          ...current,
          currentPage: resetState && !append ? 0 : current.currentPage,
          hasMore: resetState && !append ? false : current.hasMore,
          entries:
            append || preserveRows || (!resetState && current.loadedOnce)
              ? current.entries
              : [],
          totalCount:
            append || preserveRows || (!resetState && current.loadedOnce)
              ? current.totalCount
              : 0,
          loadedOnce: true,
          initialLoading: false,
          loadingMore: false,
          refreshing: false,
          error: nextError.message || "Unable to load records.",
        }));

        return null;
      }
    },
    [commitTableState, endpoint, requestFilters],
  );

  const loadMore = useCallback(async () => {
    const current = tableStateRef.current;

    if (
      !enabled ||
      current.initialLoading ||
      current.refreshing ||
      current.loadingMore ||
      !current.hasMore
    ) {
      return null;
    }

    return loadPage({
      page: current.currentPage + 1,
      append: true,
    });
  }, [enabled, loadPage]);

  const reload = useCallback(
    async ({
      preserveRows = tableStateRef.current.entries.length > 0,
      limit = CATALOG_TABLE_BATCH_SIZE,
    } = {}) =>
      loadPage({
        page: 1,
        limit,
        append: false,
        preserveRows,
      }),
    [loadPage],
  );

  const prependEntry = useCallback((entry) => {
    commitTableState((current) => {
      const alreadyPresent = current.entries.some(
        (currentEntry) => currentEntry.id === entry.id,
      );
      return {
        ...current,
        entries: [entry, ...current.entries.filter((currentEntry) => currentEntry.id !== entry.id)],
        totalCount: alreadyPresent ? current.totalCount : current.totalCount + 1,
      };
    });
  }, [commitTableState]);

  const updateEntry = useCallback((entryId, updater) => {
    commitTableState((current) => ({
      ...current,
      entries: current.entries.map((entry) =>
        entry.id === entryId
          ? typeof updater === "function"
            ? updater(entry)
            : { ...entry, ...updater }
          : entry,
      ),
    }));
  }, [commitTableState]);

  const removeEntry = useCallback((entryId) => {
    commitTableState((current) => {
      const nextEntries = current.entries.filter((entry) => entry.id !== entryId);
      return {
        ...current,
        entries: nextEntries,
        totalCount:
          nextEntries.length === current.entries.length
            ? current.totalCount
            : Math.max(0, current.totalCount - 1),
      };
    });
  }, [commitTableState]);

  const observeLoadTrigger = useCallback(
    (node) => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }

      const current = tableStateRef.current;
      if (
        !node ||
        !enabled ||
        current.initialLoading ||
        current.refreshing ||
        current.loadingMore ||
        !current.hasMore
      ) {
        return;
      }

      observerRef.current = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            loadMore();
          }
        },
        {
          root: tableShellRef.current,
          rootMargin: "0px 0px 240px 0px",
        },
      );

      observerRef.current.observe(node);
    },
    [enabled, loadMore],
  );

  useEffect(() => {
    if (!enabled) {
      return undefined;
    }

    const hasLoadedRows = tableStateRef.current.entries.length > 0;
    const endpointChanged = previousEndpointRef.current !== endpoint;
    const filtersChanged = previousRequestKeyRef.current !== requestKey;
    previousEndpointRef.current = endpoint;
    previousRequestKeyRef.current = requestKey;
    loadPage({
      page: 1,
      limit: CATALOG_TABLE_BATCH_SIZE,
      append: false,
      preserveRows: hasLoadedRows && !endpointChanged && !filtersChanged,
      resetState: endpointChanged || filtersChanged,
    });

    return undefined;
  }, [enabled, endpoint, loadPage, requestKey]);

  useEffect(() => {
    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, []);

  return {
    ...tableState,
    entries: tableState.entries,
    books: tableState.entries,
    loadMore,
    reload,
    prependEntry,
    removeEntry,
    updateEntry,
    tableShellRef,
    observeLoadTrigger,
  };
}
