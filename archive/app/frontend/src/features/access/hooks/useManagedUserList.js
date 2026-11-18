import {
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { authApi } from "../../../api/client";
import {
  CATALOG_TABLE_BATCH_SIZE,
} from "../../../utils/catalogBooks";

const USER_TABLE_LOAD_MORE_DELAY_MS = 120;

export function useManagedUserList({ enabled = true }) {
  const [userListFilters, setUserListFilters] = useState({
    q: "",
    status: "all",
    sort: "name_asc",
  });
  const [tableState, setTableState] = useState({
    rows: [],
    totalCount: 0,
    hasMore: false,
    loadedOnce: false,
    initialLoading: false,
    refreshing: false,
    error: "",
  });
  const [loadingMoreUsers, setLoadingMoreUsers] = useState(false);
  const tableShellRef = useRef(null);
  const observerRef = useRef(null);
  const loadMoreTimeoutRef = useRef(null);
  const requestIdRef = useRef(0);

  const fetchUsers = useCallback(
    async ({
      offset = 0,
      limit = CATALOG_TABLE_BATCH_SIZE,
      append = false,
      preserveRows = false,
    } = {}) => {
      if (!enabled) {
        return null;
      }

      const requestId = requestIdRef.current + 1;
      requestIdRef.current = requestId;

      setTableState((current) => {
        const keepExistingRows =
          append || preserveRows || (current.loadedOnce && !append);
        return {
          ...current,
          rows: keepExistingRows ? current.rows : [],
          totalCount: keepExistingRows ? current.totalCount : 0,
          hasMore: keepExistingRows ? current.hasMore : false,
          initialLoading:
            !append && !preserveRows && !current.loadedOnce,
          refreshing:
            !append && current.loadedOnce,
          error: "",
        };
      });

      try {
        const payload = await authApi.users({
          ...userListFilters,
          offset,
          limit,
        });
        if (requestIdRef.current !== requestId) {
          return payload;
        }

        const nextRows = payload?.rows || [];
        const totalCount = Number(payload?.pagination?.totalCount) || 0;
        setTableState((current) => ({
          rows: append ? [...current.rows, ...nextRows] : nextRows,
          totalCount,
          hasMore: Boolean(payload?.pagination?.hasMore),
          loadedOnce: true,
          initialLoading: false,
          refreshing: false,
          error: "",
        }));
        return payload;
      } catch (error) {
        if (requestIdRef.current !== requestId) {
          return null;
        }
        setTableState((current) => ({
          ...current,
          loadedOnce: true,
          initialLoading: false,
          refreshing: false,
          error: error.message || "Unable to load users.",
        }));
        return null;
      }
    },
    [enabled, userListFilters],
  );

  const loadMoreUsers = useCallback(() => {
    if (!enabled || loadingMoreUsers || !tableState.hasMore) {
      return;
    }

    setLoadingMoreUsers(true);
    if (typeof window === "undefined") {
      fetchUsers({
        offset: tableState.rows.length,
        limit: CATALOG_TABLE_BATCH_SIZE,
        append: true,
      }).finally(() => setLoadingMoreUsers(false));
      return;
    }

    if (loadMoreTimeoutRef.current) {
      window.clearTimeout(loadMoreTimeoutRef.current);
    }
    loadMoreTimeoutRef.current = window.setTimeout(() => {
      fetchUsers({
        offset: tableState.rows.length,
        limit: CATALOG_TABLE_BATCH_SIZE,
        append: true,
      }).finally(() => setLoadingMoreUsers(false));
      loadMoreTimeoutRef.current = null;
    }, USER_TABLE_LOAD_MORE_DELAY_MS);
  }, [
    enabled,
    fetchUsers,
    loadingMoreUsers,
    tableState.hasMore,
    tableState.rows.length,
  ]);

  const observeUsersLoadTrigger = useCallback(
    (node) => {
      if (observerRef.current) {
        observerRef.current.disconnect();
        observerRef.current = null;
      }

      if (
        !node ||
        !enabled ||
        !tableState.loadedOnce ||
        loadingMoreUsers ||
        !tableState.hasMore
      ) {
        return;
      }

      observerRef.current = new IntersectionObserver(
        (entries) => {
          if (entries.some((entry) => entry.isIntersecting)) {
            loadMoreUsers();
          }
        },
        {
          root: tableShellRef.current,
          rootMargin: "0px 0px 240px 0px",
        },
      );

      observerRef.current.observe(node);
    },
    [
      enabled,
      loadMoreUsers,
      loadingMoreUsers,
      tableState.hasMore,
      tableState.loadedOnce,
    ],
  );

  const reloadUsers = useCallback(
    ({
      preserveRows = tableState.rows.length > 0,
      limit = Math.max(CATALOG_TABLE_BATCH_SIZE, tableState.rows.length || 0),
    } = {}) =>
      fetchUsers({
        offset: 0,
        limit,
        preserveRows,
      }),
    [fetchUsers, tableState.rows.length],
  );

  useEffect(() => {
    setLoadingMoreUsers(false);
    if (typeof window !== "undefined" && loadMoreTimeoutRef.current) {
      window.clearTimeout(loadMoreTimeoutRef.current);
      loadMoreTimeoutRef.current = null;
    }

    if (!enabled) {
      setTableState({
        rows: [],
        totalCount: 0,
        hasMore: false,
        loadedOnce: false,
        initialLoading: false,
        refreshing: false,
        error: "",
      });
      return undefined;
    }

    tableShellRef.current?.scrollTo({ top: 0 });
    fetchUsers({ offset: 0, limit: CATALOG_TABLE_BATCH_SIZE });
    return undefined;
  }, [enabled, fetchUsers, userListFilters.q, userListFilters.sort, userListFilters.status]);

  useEffect(
    () => () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
      if (typeof window !== "undefined" && loadMoreTimeoutRef.current) {
        window.clearTimeout(loadMoreTimeoutRef.current);
      }
    },
    [],
  );

  function updateUsersFilter(key, value) {
    setUserListFilters((current) => ({
      ...current,
      [key]: value,
    }));
  }

  return {
    hasMoreManagedUsers: tableState.hasMore,
    loadingMoreUsers,
    loadingUsers: Boolean(enabled && tableState.initialLoading),
    observeUsersLoadTrigger,
    refreshUsers: reloadUsers,
    refreshingUsers: Boolean(enabled && tableState.refreshing),
    tableShellRef,
    totalManagedUsers: tableState.totalCount,
    updateUsersSearch(nextQuery) {
      updateUsersFilter("q", nextQuery);
    },
    clearUsersSearch() {
      updateUsersFilter("q", "");
    },
    updateUsersSort(nextSort) {
      updateUsersFilter("sort", nextSort);
    },
    updateUsersStatus(nextStatus) {
      updateUsersFilter("status", nextStatus);
    },
    userListFilters,
    usersError: enabled ? tableState.error : "",
    visibleManagedUsers: tableState.rows,
  };
}
