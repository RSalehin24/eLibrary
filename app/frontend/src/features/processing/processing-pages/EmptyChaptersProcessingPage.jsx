import { useEffect, useState } from "react";
import { processingFetch } from "../api";
import { useBookProcessing } from "../BookProcessingStore";
import { OverviewPanel, PageFrame } from "./processingPagePrimitives";
import { ProcessingDataCard } from "./ProcessingDataCard";

const EMPTY_SUMMARY = { total: 0, created: 0, failed: 0, processing: 0 };
const CARD_ID = "empty-chapters-records";

export function EmptyChaptersProcessingPage() {
  const {
    busyCards,
    canLoadProcessingState,
    getDomainVersion,
    forceGenerateRequests,
    recreateCompletedRequests,
  } = useBookProcessing();
  const [summary, setSummary] = useState(EMPTY_SUMMARY);
  const [summaryLoaded, setSummaryLoaded] = useState(false);
  const version = getDomainVersion(CARD_ID);

  useEffect(() => {
    if (!canLoadProcessingState) {
      return undefined;
    }
    let cancelled = false;
    processingFetch(
      `/processing/table/?card=${CARD_ID}&offset=0&limit=1&includeFacets=0`,
      { cache: "no-store" },
    )
      .then((payload) => {
        if (cancelled) {
          return;
        }
        setSummary({ ...EMPTY_SUMMARY, ...(payload?.summary || {}) });
        setSummaryLoaded(true);
      })
      .catch(() => {
        if (!cancelled) {
          setSummaryLoaded(true);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [canLoadProcessingState, version]);

  return (
    <PageFrame pageId="empty-chapters" title="Chapters without content">
      <OverviewPanel
        pageId="empty-chapters"
        loading={!summaryLoaded}
        stats={[
          {
            id: "total",
            label: "Books with missing chapters",
            value: summary.total || 0,
          },
          { id: "created", label: "Created", value: summary.created || 0 },
          { id: "failed", label: "Failed", value: summary.failed || 0 },
          {
            id: "processing",
            label: "In progress",
            value: summary.processing || 0,
          },
        ]}
      />
      <div className="processing-card-grid">
        <ProcessingDataCard
          pageId="empty-chapters"
          cardId="records"
          cardKey={CARD_ID}
          title="Books with chapters missing content"
          description="Books that were created but have one or more chapters with no content. This can happen when a chapter page could not be fetched (auth/network issue) or was genuinely empty on the source website. Regenerate to retry."
          className="processing-card-span-full processing-empty-chapters-records-card"
          bookColumnMode="wide"
          showDetailsColumn
          detailsLabel="Details"
          countPlacement="inline-tools"
          busy={Boolean(busyCards[CARD_ID])}
          actions={[
            {
              id: "regenerate",
              label: "Regenerate",
              onAction: (ids, selectedRows) => {
                const createdIds = selectedRows
                  .filter((r) => r.state === "created")
                  .map((r) => r.id);
                const otherIds = selectedRows
                  .filter((r) => r.state !== "created")
                  .map((r) => r.id);
                return Promise.all([
                  otherIds.length > 0
                    ? forceGenerateRequests(CARD_ID, otherIds)
                    : Promise.resolve(),
                  createdIds.length > 0
                    ? recreateCompletedRequests(CARD_ID, createdIds)
                    : Promise.resolve(),
                ]);
              },
            },
          ]}
        />
      </div>
    </PageFrame>
  );
}
