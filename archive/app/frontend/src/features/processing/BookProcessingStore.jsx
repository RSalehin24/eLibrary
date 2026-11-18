import { createContext, useContext, useMemo } from "react";
import { useLocation } from "react-router-dom";
import { useSession } from "../../hooks/useSession";
import { useToast } from "../../hooks/useToast";
import { hasCapability } from "../../utils/capabilities";
import {
  SHARED_PROCESSING_CARD_KEYS,
  processingPageForPathname,
} from "./store/processingStoreConfig";
import { useAutomationActions } from "./store/useAutomationActions";
import { useCatalogSyncActions } from "./store/useCatalogSyncActions";
import { useProcessingCardRunner } from "./store/useProcessingCardRunner";
import { useProcessingStateRuntime } from "./store/useProcessingStateRuntime";
import { useProcessingStream } from "./store/useProcessingStream";
import { useRequestActions } from "./store/useRequestActions";

const ProcessingPagesContext = createContext(null);

export function BookProcessingProvider({ children }) {
  const location = useLocation();
  const { authenticated, loading, user } = useSession();
  const toast = useToast();
  const canLoadProcessingState =
    authenticated && !loading && hasCapability(user, "processing:manage");
  const processingPage = processingPageForPathname(location.pathname);
  const onProcessingPage = Boolean(processingPage);
  const sharedProcessingCardKeys = useMemo(
    () => [...SHARED_PROCESSING_CARD_KEYS],
    [],
  );
  const {
    applyProcessingVersions,
    getDomainVersion,
    loadProcessingState,
    processingStateStatus,
    queueProcessingStateReload,
  } = useProcessingStateRuntime({
    canLoadProcessingState,
    onProcessingPage,
    processingPage,
    sharedProcessingCardKeys,
  });
  const streamMode = useProcessingStream({
    applyProcessingVersions,
    canLoadProcessingState,
    loadProcessingState,
    onProcessingPage,
    processingPage,
    queueProcessingStateReload,
  });
  const { busyCards, runCardAction } = useProcessingCardRunner({
    applyProcessingVersions,
    queueProcessingStateReload,
    toast,
  });
  const catalogSyncActions = useCatalogSyncActions(runCardAction);
  const automationActions = useAutomationActions(runCardAction);
  const requestActions = useRequestActions(runCardAction);

  const value = useMemo(
    () => ({
      ...automationActions,
      ...catalogSyncActions,
      ...requestActions,
      busyCards,
      canLoadProcessingState,
      getDomainVersion,
      isSharedProcessingCard: (cardKey) =>
        SHARED_PROCESSING_CARD_KEYS.has(cardKey),
      processingState: processingStateStatus.data,
      processingStateError: processingStateStatus.error,
      processingStateInitialLoading: processingStateStatus.initialLoading,
      processingStateLoaded: processingStateStatus.loadedOnce,
      processingStateRefreshing: processingStateStatus.refreshing,
      streamMode,
    }),
    [
      automationActions,
      busyCards,
      canLoadProcessingState,
      catalogSyncActions,
      getDomainVersion,
      processingStateStatus.data,
      processingStateStatus.error,
      processingStateStatus.initialLoading,
      processingStateStatus.loadedOnce,
      processingStateStatus.refreshing,
      requestActions,
      streamMode,
    ],
  );

  return (
    <ProcessingPagesContext.Provider value={value}>
      {children}
    </ProcessingPagesContext.Provider>
  );
}

export function useBookProcessing() {
  const context = useContext(ProcessingPagesContext);
  if (!context) {
    throw new Error(
      "useBookProcessing must be used within BookProcessingProvider",
    );
  }
  return context;
}
