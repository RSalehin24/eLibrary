import { useCallback } from "react";
import { processingFetch } from "../api";
import { processingPath } from "./processingStoreConfig";
import { notifyRequestAction } from "./processingNotifications";

export function useRequestActions(runCardAction) {
  const applyRequestAction = useCallback(
    (cardId, requestIds, action, extra = {}) =>
      runCardAction(
        cardId,
        () =>
          processingFetch(processingPath("/processing/requests/action/"), {
            method: "POST",
            body: {
              ids: requestIds,
              action,
              ...extra,
            },
          }),
        {
          onSuccess: (payload, nextToast) =>
            notifyRequestAction(
              nextToast,
              action,
              payload?.changedCount || 0,
              extra,
            ),
        },
      ),
    [runCardAction],
  );

  const deleteRequests = useCallback(
    (cardId, requestIds, options = {}) =>
      applyRequestAction(cardId, requestIds, "delete", {
        deleteBook: Boolean(options.deleteBook),
      }),
    [applyRequestAction],
  );

  return {
    confirmDuplicateRequests: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "confirm_duplicate"),
    createAgainRequests: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "create_again"),
    deleteRequests,
    forceGenerateRequests: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "force_generate"),
    markDuplicateRequestsAsNew: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "new"),
    markDuplicateRequestsAsNewEdition: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "new_edition"),
    pauseRequests: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "pause"),
    recreateCompletedRequests: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "recreate"),
    resumePausedRequests: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "resume"),
    retryFailedRequests: (cardId, requestIds) =>
      applyRequestAction(cardId, requestIds, "retry"),
  };
}
