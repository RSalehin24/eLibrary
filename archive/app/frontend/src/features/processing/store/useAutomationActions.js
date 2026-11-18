import { useCallback } from "react";
import { processingFetch } from "../api";
import {
  PROCESSING_SYNC_SCOPE_CATALOG,
  PROCESSING_SYNC_SCOPE_INCOMPLETE,
  processingPath,
  scopedSyncPath
} from "./processingStoreConfig";

function useAutomationGroup({ cardId, runMode, runPath, savePath, scope, text }, runCardAction) {
  const save = useCallback(
    (form) =>
      runCardAction(
        `${cardId}-save`,
        () => processingFetch(processingPath(savePath), { method: "POST", body: form }),
        {
          onSuccess: (_, nextToast) =>
            nextToast.success({
              title: `${text.title} saved`,
              description: "The schedule settings were updated."
            })
        }
      ),
    [cardId, runCardAction, savePath, text.title]
  );

  const run = useCallback(
    () =>
      runCardAction(
        `${cardId}-run`,
        () => processingFetch(processingPath(runPath), { method: "POST" }),
        {
          onSuccess: (_, nextToast) =>
            nextToast.info({
              title: text.runTitle,
              description: text.runDescription
            })
        }
      ),
    [cardId, runCardAction, runPath, text.runDescription, text.runTitle]
  );

  const pause = useCallback(
    () =>
      runCardAction(
        `${cardId}-run`,
        () =>
          processingFetch(processingPath(scopedSyncPath(scope, "pause")), {
            method: "POST"
          }),
        {
          onSuccess: (_, nextToast) =>
            nextToast.info({
              title: text.pauseTitle,
              description: text.pauseDescription
            })
        }
      ),
    [cardId, runCardAction, scope, text.pauseDescription, text.pauseTitle]
  );

  const resume = useCallback(
    () =>
      runCardAction(
        `${cardId}-run`,
        () =>
          processingFetch(processingPath(scopedSyncPath(scope, "resume")), {
            method: "POST",
            body: { runMode }
          }),
        {
          onSuccess: (_, nextToast) =>
            nextToast.info({
              title: text.resumeTitle,
              description: text.resumeDescription
            })
        }
      ),
    [cardId, runCardAction, runMode, scope, text.resumeDescription, text.resumeTitle]
  );

  const stop = useCallback(
    () =>
      runCardAction(`${cardId}-run`, () =>
        processingFetch(processingPath(scopedSyncPath(scope, "stop")), {
          method: "POST"
        })
      ),
    [cardId, runCardAction, scope]
  );

  return { pause, resume, run, save, stop };
}

export function useAutomationActions(runCardAction) {
  const catalog = useAutomationGroup(
    {
      cardId: "catalog-automation",
      runMode: "catalog_automation",
      runPath: "/processing/automation/catalog/run/",
      savePath: "/processing/automation/catalog/",
      scope: PROCESSING_SYNC_SCOPE_CATALOG,
      text: {
        title: "Catalog automation",
        runTitle: "Catalog automation running",
        runDescription: "Catalog automation picked up the shared catalog work.",
        pauseTitle: "Catalog automation pausing",
        pauseDescription:
          "Automated catalog sync will pause after the current page finishes.",
        resumeTitle: "Catalog automation resumed",
        resumeDescription: "Catalog automation resumed shared progress."
      }
    },
    runCardAction
  );
  const incomplete = useAutomationGroup(
    {
      cardId: "incomplete-automation",
      runMode: "incomplete_automation",
      runPath: "/processing/automation/incomplete/run/",
      savePath: "/processing/automation/incomplete/",
      scope: PROCESSING_SYNC_SCOPE_INCOMPLETE,
      text: {
        title: "Incomplete automation",
        runTitle: "Incomplete automation started",
        runDescription: "Incomplete catalog sync is running.",
        pauseTitle: "Incomplete automation pausing",
        pauseDescription: "Incomplete catalog sync will pause after the current batch.",
        resumeTitle: "Incomplete automation resumed",
        resumeDescription: "Incomplete catalog sync restarted from the beginning."
      }
    },
    runCardAction
  );

  return {
    pauseCatalogAutomation: catalog.pause,
    pauseIncompleteAutomation: incomplete.pause,
    resumeCatalogAutomation: catalog.resume,
    resumeIncompleteAutomation: incomplete.resume,
    runCatalogAutomation: catalog.run,
    runIncompleteAutomation: incomplete.run,
    saveCatalogAutomation: catalog.save,
    saveIncompleteAutomation: incomplete.save,
    stopCatalogAutomation: catalog.stop,
    stopIncompleteAutomation: incomplete.stop
  };
}
