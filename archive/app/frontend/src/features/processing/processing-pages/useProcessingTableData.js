import { useCallback, useEffect, useRef, useState } from "react";
import { processingFetch } from "../api";
import { useBookProcessing } from "../BookProcessingStore";
import { PROCESSING_CARD_VISIBILITY_ROOT_MARGIN, PROCESSING_TABLE_BATCH_SIZE } from "./processingPageModel";
import { processingCardCountFromState } from "./processingCardState";
import { processingTablePath } from "./processingTableRows";
export function useProcessingTableData({ cardKey, filters, enabled }) {
  const { getDomainVersion, processingState, processingStateLoaded } = useBookProcessing();
  const visibilityObserverRef = useRef(null);
  const fetchInFlightRequestIdRef = useRef(0);
  const [visibilityNode, setVisibilityNode] = useState(null);
  const tableShellRef = useRef(null);
  const observerRef = useRef(null);
  const loadMoreTimerRef = useRef(null);
  const requestIdRef = useRef(0);
  const latestKnownVersion = getDomainVersion(cardKey);
  const filtersActive = Boolean(filters.q || filters.category || filters.status);
  const sharedCount = filtersActive ? null : processingCardCountFromState(cardKey, processingState);
  const filterSignature = `${filters.q}::${filters.category}::${filters.status}`;
  const [isVisible, setIsVisible] = useState(typeof window === "undefined" || typeof IntersectionObserver === "undefined");
  const [tableState, setTableState] = useState({
    rows: [],
    totalCount: 0,
    categoryOptions: [],
    statusOptions: [],
    hasMore: false,
    latestKnownVersion,
    loadedVersion: 0,
    loadedOnce: false,
    initialLoading: false,
    refreshing: false,
    error: ""
  });
  const [loadingMore, setLoadingMore] = useState(false);
  const fetchTable = useCallback(async ({
    offset = 0,
    limit = PROCESSING_TABLE_BATCH_SIZE,
    append = false,
    includeFacets = true,
    hardReload = false
  }) => {
    if (!enabled) {
      return null;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    fetchInFlightRequestIdRef.current = requestId;
    setTableState(current => ({
      ...current,
      latestKnownVersion: Math.max(current.latestKnownVersion, latestKnownVersion),
      loadedOnce: append ? current.loadedOnce : hardReload ? false : current.loadedOnce,
      initialLoading: !append && (!current.loadedOnce || hardReload),
      refreshing: !append && current.loadedOnce && !hardReload,
      error: ""
    }));
    try {
      const payload = await processingFetch(processingTablePath(cardKey, filters, offset, limit, includeFacets), {
        cache: "no-store"
      });
      if (requestIdRef.current !== requestId) {
        return payload;
      }
      const loadedVersion = Number(payload?.version || latestKnownVersion || 0);
      setTableState(current => ({
        rows: append ? [...current.rows, ...(payload.rows || [])] : payload.rows || [],
        totalCount: payload?.pagination?.totalCount ?? payload?.totalCount ?? current.totalCount,
        categoryOptions: payload?.filters?.categoryOptions || current.categoryOptions,
        statusOptions: payload?.filters?.statusOptions || current.statusOptions,
        hasMore: Boolean(payload?.pagination?.hasMore),
        latestKnownVersion: Math.max(current.latestKnownVersion, loadedVersion),
        loadedVersion,
        loadedOnce: true,
        initialLoading: false,
        refreshing: false,
        error: ""
      }));
      return payload;
    } catch (loadError) {
      if (requestIdRef.current !== requestId) {
        return null;
      }
      setTableState(current => ({
        ...current,
        initialLoading: false,
        refreshing: false,
        error: loadError.message || "Unable to load processing table."
      }));
      return null;
    } finally {
      if (fetchInFlightRequestIdRef.current === requestId) {
        fetchInFlightRequestIdRef.current = 0;
      }
    }
  }, [cardKey, enabled, filters, latestKnownVersion]);
  const loadMore = useCallback(() => {
    if (!enabled || !tableState.hasMore || loadingMore || fetchInFlightRequestIdRef.current) {
      return;
    }
    setLoadingMore(true);
    if (typeof window === "undefined") {
      fetchTable({
        offset: tableState.rows.length,
        limit: PROCESSING_TABLE_BATCH_SIZE,
        append: true,
        includeFacets: false
      }).finally(() => setLoadingMore(false));
      return;
    }
    if (loadMoreTimerRef.current) {
      window.clearTimeout(loadMoreTimerRef.current);
    }
    loadMoreTimerRef.current = window.setTimeout(() => {
      fetchTable({
        offset: tableState.rows.length,
        limit: PROCESSING_TABLE_BATCH_SIZE,
        append: true,
        includeFacets: false
      }).finally(() => setLoadingMore(false));
      loadMoreTimerRef.current = null;
    }, 120);
  }, [enabled, fetchTable, loadingMore, tableState.hasMore, tableState.rows.length]);
  const observeLoadTrigger = useCallback(node => {
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
    if (!node || !enabled || !tableState.loadedOnce || loadingMore || !tableState.hasMore || fetchInFlightRequestIdRef.current) {
      return;
    }
    observerRef.current = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) {
        loadMore();
      }
    }, {
      root: tableShellRef.current,
      rootMargin: "0px 0px 240px 0px"
    });
    observerRef.current.observe(node);
  }, [enabled, fetchInFlightRequestIdRef, loadingMore, loadMore, tableState.hasMore, tableState.loadedOnce]);
  useEffect(() => {
    if (typeof window === "undefined" || typeof IntersectionObserver === "undefined") {
      setIsVisible(true);
      return undefined;
    }
    if (visibilityObserverRef.current) {
      visibilityObserverRef.current.disconnect();
      visibilityObserverRef.current = null;
    }
    if (!visibilityNode || !enabled) {
      return undefined;
    }
    visibilityObserverRef.current = new IntersectionObserver(entries => {
      if (entries.length) {
        setIsVisible(entries.some(entry => entry.isIntersecting));
      }
    }, {
      root: null,
      rootMargin: PROCESSING_CARD_VISIBILITY_ROOT_MARGIN,
      threshold: 0.1
    });
    visibilityObserverRef.current.observe(visibilityNode);
    return () => {
      if (visibilityObserverRef.current) {
        visibilityObserverRef.current.disconnect();
        visibilityObserverRef.current = null;
      }
    };
  }, [enabled, visibilityNode]);
  useEffect(() => {
    setLoadingMore(false);
    if (typeof window !== "undefined" && loadMoreTimerRef.current) {
      window.clearTimeout(loadMoreTimerRef.current);
      loadMoreTimerRef.current = null;
    }
    requestIdRef.current += 1;
    fetchInFlightRequestIdRef.current = 0;
    if (!enabled) {
      setTableState({
        rows: [],
        totalCount: 0,
        categoryOptions: [],
        statusOptions: [],
        hasMore: false,
        latestKnownVersion,
        loadedVersion: 0,
        loadedOnce: false,
        initialLoading: false,
        refreshing: false,
        error: ""
      });
      return undefined;
    }
    setTableState(current => ({
      ...current,
      rows: [],
      totalCount: 0,
      categoryOptions: [],
      statusOptions: [],
      hasMore: false,
      latestKnownVersion,
      loadedVersion: 0,
      loadedOnce: false,
      initialLoading: false,
      refreshing: false,
      error: ""
    }));
    return undefined;
  }, [cardKey, enabled, filterSignature]);
  useEffect(() => {
    if (!enabled) {
      return undefined;
    }
    setTableState(current => ({
      ...current,
      latestKnownVersion: Math.max(current.latestKnownVersion, latestKnownVersion)
    }));
    if (!tableState.loadedOnce && !filtersActive && processingStateLoaded && sharedCount === 0) {
      setTableState(current => ({
        ...current,
        rows: [],
        totalCount: 0,
        categoryOptions: [],
        statusOptions: [],
        hasMore: false,
        latestKnownVersion: Math.max(current.latestKnownVersion, latestKnownVersion),
        loadedVersion: latestKnownVersion,
        loadedOnce: true,
        initialLoading: false,
        refreshing: false,
        error: ""
      }));
      return undefined;
    }
    if (!tableState.loadedOnce) {
      if (!filtersActive && !processingStateLoaded) {
        return undefined;
      }
      if (!isVisible) {
        return undefined;
      }
      if (fetchInFlightRequestIdRef.current) {
        return undefined;
      }
      fetchTable({
        offset: 0,
        limit: PROCESSING_TABLE_BATCH_SIZE,
        includeFacets: true,
        hardReload: false
      });
      return undefined;
    }
    if (!isVisible) {
      return undefined;
    }
    if (latestKnownVersion <= tableState.loadedVersion) {
      return undefined;
    }
    if (fetchInFlightRequestIdRef.current) {
      return undefined;
    }
    fetchTable({
      offset: 0,
      limit: tableState.rows.length > 0 ? tableState.rows.length : PROCESSING_TABLE_BATCH_SIZE,
      includeFacets: false,
      hardReload: false
    });
    return undefined;
  }, [enabled, fetchTable, filtersActive, isVisible, latestKnownVersion, processingStateLoaded, sharedCount, tableState.loadedOnce, tableState.loadedVersion, tableState.rows.length]);
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && loadMoreTimerRef.current) {
        window.clearTimeout(loadMoreTimerRef.current);
      }
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
      if (visibilityObserverRef.current) {
        visibilityObserverRef.current.disconnect();
      }
    };
  }, []);
  return {
    rows: tableState.rows,
    totalCount: tableState.totalCount,
    categoryOptions: tableState.categoryOptions,
    statusOptions: tableState.statusOptions,
    hasMore: tableState.hasMore,
    loadedOnce: enabled ? tableState.loadedOnce : false,
    initialLoading: Boolean(enabled && tableState.initialLoading),
    loadingMore,
    refreshing: Boolean(enabled && tableState.refreshing),
    error: enabled ? tableState.error : "",
    loadMore,
    setCardVisibilityNode: setVisibilityNode,
    tableShellRef,
    observeLoadTrigger
  };
}
