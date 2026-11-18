import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { processingFetch } from "../api";
import { useBookProcessing } from "../BookProcessingStore";
import { processingCardFromState } from "./processingCardState";
import { processingCardPath } from "./processingTableRows";
export function useProcessingCardData({
  cardKey,
  enabled
}) {
  const {
    getDomainVersion,
    isSharedProcessingCard,
    processingState,
    processingStateLoaded,
    processingStateInitialLoading,
    processingStateRefreshing,
    processingStateError
  } = useBookProcessing();
  const usesSharedState = enabled && isSharedProcessingCard(cardKey);
  const latestKnownVersion = getDomainVersion(cardKey);
  const requestIdRef = useRef(0);
  const loadedVersionRef = useRef(latestKnownVersion);
  const [cardState, setCardState] = useState({
    data: null,
    loadedOnce: false,
    initialLoading: false,
    refreshing: false,
    error: ""
  });
  const sharedCardData = useMemo(() => usesSharedState ? processingCardFromState(cardKey, processingState) : null, [cardKey, processingState, usesSharedState]);
  const loadCard = useCallback(() => {
    if (!enabled || usesSharedState) {
      setCardState({
        data: null,
        loadedOnce: false,
        initialLoading: false,
        refreshing: false,
        error: ""
      });
      return Promise.resolve(null);
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setCardState(current => ({
      ...current,
      initialLoading: !current.loadedOnce,
      refreshing: current.loadedOnce,
      error: ""
    }));
    return processingFetch(processingCardPath(cardKey), {
      cache: "no-store"
    }).then(payload => {
      if (requestIdRef.current !== requestId) {
        return payload;
      }
      setCardState({
        data: payload,
        loadedOnce: true,
        initialLoading: false,
        refreshing: false,
        error: ""
      });
      return payload;
    }).catch(loadError => {
      if (requestIdRef.current !== requestId) {
        return null;
      }
      setCardState(current => ({
        ...current,
        loadedOnce: true,
        initialLoading: false,
        refreshing: false,
        error: loadError.message || "Unable to load processing card."
      }));
      return null;
    });
  }, [cardKey, enabled, usesSharedState]);
  useEffect(() => {
    if (usesSharedState) {
      return undefined;
    }
    loadCard();
    return undefined;
  }, [loadCard, usesSharedState]);
  useEffect(() => {
    if (usesSharedState || !enabled || !["syncing", "pausing"].includes(cardState.data?.sync?.status || "")) {
      return undefined;
    }
    const timerId = window.setInterval(() => {
      loadCard();
    }, 2000);
    return () => {
      window.clearInterval(timerId);
    };
  }, [cardState.data?.sync?.status, enabled, loadCard, usesSharedState]);
  useEffect(() => {
    if (usesSharedState || !enabled || !cardState.loadedOnce) {
      loadedVersionRef.current = latestKnownVersion;
      return undefined;
    }
    if (latestKnownVersion <= loadedVersionRef.current) {
      return undefined;
    }
    loadedVersionRef.current = latestKnownVersion;
    loadCard();
    return undefined;
  }, [cardState.loadedOnce, enabled, latestKnownVersion, loadCard, usesSharedState]);
  if (usesSharedState) {
    return {
      data: sharedCardData,
      loadedOnce: enabled ? processingStateLoaded : false,
      initialLoading: Boolean(enabled && processingStateInitialLoading),
      refreshing: Boolean(enabled && processingStateRefreshing),
      error: enabled ? processingStateError : ""
    };
  }
  return {
    data: cardState.data,
    loadedOnce: enabled ? cardState.loadedOnce : false,
    initialLoading: Boolean(enabled && cardState.initialLoading),
    refreshing: Boolean(enabled && cardState.refreshing),
    error: enabled ? cardState.error : ""
  };
}
