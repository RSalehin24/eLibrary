import { useCallback, useState } from "react";

export function useProcessingCardRunner({
  applyProcessingVersions,
  queueProcessingStateReload,
  toast
}) {
  const [busyCards, setBusyCards] = useState({});

  const runCardAction = useCallback(
    async (cardId, request, options = {}) => {
      setBusyCards((current) => ({
        ...current,
        [cardId]: (current[cardId] || 0) + 1
      }));
      try {
        const payload = await request();
        const versionUpdate = applyProcessingVersions(payload?.versions || {});
        if (versionUpdate.sharedChanged) {
          queueProcessingStateReload();
        }
        if (typeof options.onSuccess === "function") {
          options.onSuccess(payload, toast);
        }
        return payload;
      } catch (actionError) {
        const message =
          options.errorMessage ||
          actionError.message ||
          "Unable to complete the action.";
        if (![401, 403].includes(actionError?.status)) {
          toast.error(message);
        }
        return null;
      } finally {
        setBusyCards((current) => {
          const currentCount = current[cardId] || 0;
          const next = { ...current };
          if (currentCount > 1) {
            next[cardId] = currentCount - 1;
          } else {
            delete next[cardId];
          }
          return next;
        });
      }
    },
    [applyProcessingVersions, queueProcessingStateReload, toast]
  );

  return { busyCards, runCardAction };
}
