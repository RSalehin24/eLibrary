import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { processingFetch } from "../api";
import {
  PROCESSING_CARD_KEYS,
  SHARED_PROCESSING_CARD_KEYS,
  normalizeVersionValue,
  processingPath,
  versionSignature
} from "./processingStoreConfig";

const EMPTY_STATUS = {
  data: null,
  loadedOnce: false,
  initialLoading: false,
  refreshing: false,
  error: ""
};

export function useProcessingStateRuntime({
  canLoadProcessingState,
  onProcessingPage,
  processingPage,
  sharedProcessingCardKeys
}) {
  const [domainVersions, setDomainVersions] = useState({});
  const [processingStateStatus, setProcessingStateStatus] = useState(EMPTY_STATUS);
  const sharedVersionSignature = useMemo(
    () => versionSignature(domainVersions, sharedProcessingCardKeys),
    [domainVersions, sharedProcessingCardKeys]
  );
  const loadProcessingStateRef = useRef(() => Promise.resolve(null));
  const loadPromiseRef = useRef(null);
  const reloadQueuedRef = useRef(false);
  const requestIdRef = useRef(0);
  const appliedRequestIdRef = useRef(0);
  const appliedSharedSignatureRef = useRef("");
  const lastLoadedPageRef = useRef("");
  const sharedVersionSignatureRef = useRef(sharedVersionSignature);
  const domainVersionsRef = useRef(domainVersions);
  const queuedSharedSignatureRef = useRef("");

  useEffect(() => {
    sharedVersionSignatureRef.current = sharedVersionSignature;
  }, [sharedVersionSignature]);

  useEffect(() => {
    domainVersionsRef.current = domainVersions;
  }, [domainVersions]);

  const applyProcessingVersions = useCallback((incomingVersions) => {
    if (!incomingVersions || typeof incomingVersions !== "object") {
      return { changed: false, sharedChanged: false };
    }

    let changed = false;
    let sharedChanged = false;
    const currentVersions = domainVersionsRef.current || {};
    const nextVersions = { ...currentVersions };
    Object.entries(incomingVersions).forEach(([domain, rawValue]) => {
      if (!PROCESSING_CARD_KEYS.includes(domain)) return;
      const nextValue = normalizeVersionValue(rawValue);
      if (nextValue <= normalizeVersionValue(nextVersions[domain])) return;
      nextVersions[domain] = nextValue;
      changed = true;
      if (SHARED_PROCESSING_CARD_KEYS.has(domain)) {
        sharedChanged = true;
      }
    });
    if (!changed) return { changed: false, sharedChanged: false };

    domainVersionsRef.current = nextVersions;
    sharedVersionSignatureRef.current = versionSignature(
      nextVersions,
      sharedProcessingCardKeys
    );
    setDomainVersions(nextVersions);
    return { changed, sharedChanged };
  }, [sharedProcessingCardKeys]);

  const getDomainVersion = useCallback(
    (cardKey) => normalizeVersionValue(domainVersions[cardKey]),
    [domainVersions]
  );

  const loadProcessingState = useCallback(() => {
    if (!onProcessingPage || !canLoadProcessingState) {
      return Promise.resolve(null);
    }
    if (loadPromiseRef.current) {
      const currentSharedSignature = sharedVersionSignatureRef.current;
      if (currentSharedSignature !== queuedSharedSignatureRef.current) {
        queuedSharedSignatureRef.current = currentSharedSignature;
        reloadQueuedRef.current = true;
      }
      return loadPromiseRef.current;
    }

    let disposed = false;
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    queuedSharedSignatureRef.current = sharedVersionSignatureRef.current;
    setProcessingStateStatus((current) => ({
      ...current,
      initialLoading: !current.loadedOnce,
      refreshing: current.loadedOnce,
      error: ""
    }));

    const request = processingFetch(processingPath("/processing/state/"), {
      cache: "no-store"
    })
      .then((payload) => {
        if (disposed || requestId < appliedRequestIdRef.current) return payload;
        appliedRequestIdRef.current = requestId;
        const payloadVersions = payload?.versions || {};
        applyProcessingVersions(payload?.versions || {});
        const payloadSharedSignature = versionSignature(
          payloadVersions,
          sharedProcessingCardKeys
        );
        const knownSharedSignature = versionSignature(
          domainVersionsRef.current || {},
          sharedProcessingCardKeys
        );
        appliedSharedSignatureRef.current = payloadSharedSignature;
        sharedVersionSignatureRef.current = knownSharedSignature;
        if (
          queuedSharedSignatureRef.current === payloadSharedSignature &&
          knownSharedSignature === payloadSharedSignature
        ) {
          reloadQueuedRef.current = false;
        }
        if (knownSharedSignature !== payloadSharedSignature) {
          setProcessingStateStatus((current) => ({
            ...current,
            initialLoading: !current.loadedOnce,
            refreshing: current.loadedOnce,
            error: ""
          }));
          return payload;
        }
        setProcessingStateStatus({
          data: payload,
          loadedOnce: true,
          initialLoading: false,
          refreshing: false,
          error: ""
        });
        return payload;
      })
      .catch((loadError) => {
        if (disposed || requestId < appliedRequestIdRef.current) return null;
        setProcessingStateStatus((current) => ({
          ...current,
          loadedOnce: true,
          initialLoading: false,
          refreshing: false,
          error: loadError.message || "Unable to load processing state."
        }));
        return null;
      })
      .finally(() => {
        disposed = true;
        if (loadPromiseRef.current === request) {
          loadPromiseRef.current = null;
        }
        const shouldReload =
          reloadQueuedRef.current ||
          sharedVersionSignatureRef.current !== appliedSharedSignatureRef.current;
        reloadQueuedRef.current = false;
        if (shouldReload && onProcessingPage && canLoadProcessingState) {
          void loadProcessingStateRef.current?.();
        }
      });
    loadPromiseRef.current = request;
    return request;
  }, [
    applyProcessingVersions,
    canLoadProcessingState,
    onProcessingPage,
    sharedProcessingCardKeys
  ]);

  useEffect(() => {
    loadProcessingStateRef.current = loadProcessingState;
  }, [loadProcessingState]);

  const queueProcessingStateReload = useCallback(() => {
    if (!onProcessingPage || !canLoadProcessingState) return;
    if (loadPromiseRef.current) {
      reloadQueuedRef.current = true;
      return;
    }
    void loadProcessingStateRef.current?.();
  }, [canLoadProcessingState, onProcessingPage]);

  useEffect(() => {
    if (canLoadProcessingState) return undefined;
    setDomainVersions({});
    setProcessingStateStatus(EMPTY_STATUS);
    loadPromiseRef.current = null;
    reloadQueuedRef.current = false;
    appliedRequestIdRef.current = 0;
    appliedSharedSignatureRef.current = "";
    queuedSharedSignatureRef.current = "";
    lastLoadedPageRef.current = "";
    return undefined;
  }, [canLoadProcessingState]);

  useEffect(() => {
    if (!onProcessingPage || !canLoadProcessingState) {
      setProcessingStateStatus(EMPTY_STATUS);
      loadPromiseRef.current = null;
      reloadQueuedRef.current = false;
      appliedRequestIdRef.current = 0;
      appliedSharedSignatureRef.current = "";
      queuedSharedSignatureRef.current = "";
      lastLoadedPageRef.current = "";
      return undefined;
    }
    const pageChanged = lastLoadedPageRef.current !== processingPage;
    if (pageChanged) lastLoadedPageRef.current = processingPage;
    if (
      pageChanged ||
      !processingStateStatus.loadedOnce ||
      sharedVersionSignature !== appliedSharedSignatureRef.current
    ) {
      if (loadPromiseRef.current) {
        return undefined;
      }
      loadProcessingState();
    }
    return undefined;
  }, [
    canLoadProcessingState,
    loadProcessingState,
    onProcessingPage,
    processingPage,
    processingStateStatus.loadedOnce,
    sharedVersionSignature
  ]);

  return {
    applyProcessingVersions,
    domainVersions,
    getDomainVersion,
    loadProcessingState,
    processingStateStatus,
    queueProcessingStateReload
  };
}
