import { useCallback } from "react";
import { processingFetch } from "../api";
import {
  PROCESSING_SYNC_SCOPE_CATALOG,
  catalogRemotePages,
  processingPath,
  scopedSyncPath
} from "./processingStoreConfig";
import { requestCountLabel } from "./processingNotifications";

export function useCatalogSyncActions(runCardAction) {
  const startCatalogSync = useCallback(
    (remotePages) =>
      runCardAction(
        "catalog-sync",
        () =>
          processingFetch(processingPath("/processing/sync/start/"), {
            method: "POST",
            ...(catalogRemotePages(remotePages).length
              ? { body: { remotePages: catalogRemotePages(remotePages) } }
              : {})
          }),
        {
          onSuccess: (_, nextToast) =>
            nextToast.info({
              title: "Sync started",
              description: "Catalog sync is running."
            })
        }
      ),
    [runCardAction]
  );

  const pauseCatalogSync = useCallback(
    () =>
      runCardAction(
        "catalog-sync",
        () =>
          processingFetch(
            processingPath(scopedSyncPath(PROCESSING_SYNC_SCOPE_CATALOG, "pause")),
            { method: "POST" }
          ),
        {
          onSuccess: (_, nextToast) =>
            nextToast.info({
              title: "Pause requested",
              description: "Catalog sync will pause after the current page."
            })
        }
      ),
    [runCardAction]
  );

  const resumeCatalogSync = useCallback(
    () =>
      runCardAction(
        "catalog-sync",
        () =>
          processingFetch(
            processingPath(scopedSyncPath(PROCESSING_SYNC_SCOPE_CATALOG, "resume")),
            { method: "POST", body: { runMode: "manual" } }
          ),
        {
          onSuccess: (_, nextToast) =>
            nextToast.info({
              title: "Sync resumed",
              description: "Catalog sync resumed from the saved endpoint."
            })
        }
      ),
    [runCardAction]
  );

  const stopCatalogSync = useCallback(
    () =>
      runCardAction("catalog-sync", () =>
        processingFetch(
          processingPath(scopedSyncPath(PROCESSING_SYNC_SCOPE_CATALOG, "stop")),
          { method: "POST" }
        )
      ),
    [runCardAction]
  );

  const createRequestsForRecords = useCallback(
    (recordIds) =>
      runCardAction(
        "catalog-records",
        () =>
          processingFetch(processingPath("/processing/records/create-requests/"), {
            method: "POST",
            body: { ids: recordIds }
          }),
        {
          onSuccess: (payload, nextToast) => {
            if (payload?.createdCount) {
              nextToast.success({
                title: "Requests created",
                description: `${requestCountLabel(
                  payload.createdCount,
                  "request"
                )} entered the pipeline.`
              });
              return;
            }
            nextToast.info({
              title: "No requests created",
              description: "The selected records already have active requests."
            });
          }
        }
      ),
    [runCardAction]
  );

  return {
    createRequestsForRecords,
    pauseCatalogSync,
    resumeCatalogSync,
    startCatalogSync,
    stopCatalogSync
  };
}
