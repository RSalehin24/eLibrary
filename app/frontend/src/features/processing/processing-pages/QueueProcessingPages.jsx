import {
  DEFAULT_AUTOMATION_CARD,
  DEFAULT_SYNC_CARD,
} from "./processingPageModel";
import BookRouteLink from "../../../components/BookRouteLink";
import { OverviewPanel, PageFrame } from "./processingPagePrimitives";
import { AutomationPanel } from "./AutomationPanel";
import { ProcessingDataCard } from "./ProcessingDataCard";
import { useBookProcessing } from "../BookProcessingStore";
import { useProcessingCardData } from "./useProcessingCardData";
function CreateCard({
  cardId,
  cardKey,
  title,
  description,
  actions,
  actionLabel,
  renderRowAction,
}) {
  const { busyCards } = useBookProcessing();
  return (
    <ProcessingDataCard
      pageId="create"
      cardId={cardId}
      cardKey={cardKey}
      title={title}
      description={description}
      busy={Boolean(busyCards[`create-${cardId}`])}
      className="processing-inline-count-card processing-create-card"
      showDetailsColumn={false}
      countPlacement="inline-tools"
      actions={actions}
      actionLabel={actionLabel}
      renderRowAction={renderRowAction}
    />
  );
}
export function CreateProcessingPage() {
  const { canLoadProcessingState, deleteRequests, pauseRequests } =
    useBookProcessing();
  const { data: createOverviewCard, loadedOnce: createOverviewLoaded } =
    useProcessingCardData({
      cardKey: "create-overview",
      enabled: canLoadProcessingState,
    });
  const summary = createOverviewCard?.summary || {};
  return (
    <PageFrame pageId="create" title="Create">
      <OverviewPanel
        pageId="create"
        loading={!createOverviewLoaded}
        stats={[
          {
            id: "queue",
            label: "Queue",
            value: summary.queue || 0,
          },
          {
            id: "processing",
            label: "Processing",
            value: summary.processing || 0,
          },
          {
            id: "created",
            label: "Created",
            value: summary.created || 0,
          },
          {
            id: "requests",
            label: "Requests",
            value: summary.requests || 0,
          },
        ]}
      />
      <div className="processing-card-grid">
        <CreateCard
          cardId="queue"
          cardKey="create-queue"
          title="Queue"
          description="Requests waiting for the processor."
          actions={[
            {
              id: "delete",
              label: "Delete",
              danger: true,
              onAction: (ids) => deleteRequests("create-queue", ids),
            },
          ]}
        />
        <CreateCard
          cardId="processing"
          cardKey="create-processing"
          title="Processing"
          description="Requests currently being built."
          actions={[
            {
              id: "pause",
              label: "Pause",
              onAction: (ids) => pauseRequests("create-processing", ids),
            },
            {
              id: "delete",
              label: "Delete",
              danger: true,
              onAction: (ids) => deleteRequests("create-processing", ids),
            },
          ]}
        />
        <CreateCard
          cardId="created"
          cardKey="create-created"
          title="Created"
          description="Completed books."
          actionLabel="Open"
          renderRowAction={(row) =>
            row.linkedBookSlug ? (
              <BookRouteLink
                slug={row.linkedBookSlug}
                className="ghost-button table-row-action"
                data-testid={`create-created-open-${row.id}`}
              >
                Open
              </BookRouteLink>
            ) : null
          }
          actions={[
            {
              id: "delete",
              label: "Delete",
              danger: true,
              onAction: (ids) =>
                deleteRequests("create-created", ids, {
                  deleteBook: true,
                }),
            },
          ]}
        />
        <CreateCard
          cardId="requests"
          cardKey="create-requests"
          title="Requests"
          description="New book creation requests."
          actions={[
            {
              id: "delete",
              label: "Delete",
              danger: true,
              onAction: (ids) => deleteRequests("create-requests", ids),
            },
          ]}
        />
      </div>
    </PageFrame>
  );
}
function OnHoldCard({
  cardId,
  cardKey,
  title,
  description,
  actions,
  detailsLabel,
  className = "",
}) {
  const { busyCards } = useBookProcessing();
  return (
    <ProcessingDataCard
      pageId="on-hold"
      cardId={cardId}
      cardKey={cardKey}
      title={title}
      description={description}
      busy={Boolean(busyCards[`on-hold-${cardId}`])}
      countPlacement="inline-tools"
      actions={actions}
      detailsLabel={detailsLabel}
      className={`processing-inline-count-card${className ? ` ${className}` : ""}`}
    />
  );
}
export function OnHoldProcessingPage() {
  const {
    canLoadProcessingState,
    forceGenerateRequests,
    resumePausedRequests,
    retryFailedRequests,
    markDuplicateRequestsAsNew,
    markDuplicateRequestsAsNewEdition,
    confirmDuplicateRequests,
    createAgainRequests,
    deleteRequests,
  } = useBookProcessing();
  const { data: onHoldOverviewCard, loadedOnce: onHoldOverviewLoaded } =
    useProcessingCardData({
      cardKey: "on-hold-overview",
      enabled: canLoadProcessingState,
    });
  const summary = onHoldOverviewCard?.summary || {};
  return (
    <PageFrame pageId="on-hold" title="On Hold">
      <OverviewPanel
        pageId="on-hold"
        loading={!onHoldOverviewLoaded}
        stats={[
          {
            id: "paused",
            label: "Paused",
            value: summary.paused || 0,
          },
          {
            id: "failed",
            label: "Failed",
            value: summary.failed || 0,
          },
          {
            id: "duplicate",
            label: "Duplicate",
            value: summary.duplicate || 0,
          },
          {
            id: "deleted",
            label: "Deleted",
            value: summary.deleted || 0,
          },
        ]}
      />
      <div className="processing-card-grid">
        <OnHoldCard
          cardId="paused"
          cardKey="on-hold-paused"
          title="Paused"
          description="Requests with saved progress."
          actions={[
            {
              id: "resume",
              label: "Resume",
              onAction: (ids) => resumePausedRequests("on-hold-paused", ids),
            },
            {
              id: "delete",
              label: "Delete",
              danger: true,
              onAction: (ids) => deleteRequests("on-hold-paused", ids),
            },
          ]}
        />
        <OnHoldCard
          cardId="failed"
          cardKey="on-hold-failed"
          title="Failed"
          description="Requests that need retry or deletion."
          detailsLabel="Error Reason"
          className="processing-on-hold-failed-card"
          actions={[
            {
              id: "force-generate",
              label: "Force Generate",
              onAction: (ids) => forceGenerateRequests("on-hold-failed", ids),
            },
            {
              id: "retry",
              label: "Retry",
              onAction: (ids) => retryFailedRequests("on-hold-failed", ids),
            },
            {
              id: "delete",
              label: "Delete",
              danger: true,
              onAction: (ids) => deleteRequests("on-hold-failed", ids),
            },
          ]}
        />
        <OnHoldCard
          cardId="duplicate"
          cardKey="on-hold-duplicate"
          title="Duplicate"
          description="Requests waiting on duplicate resolution."
          actions={[
            {
              id: "new",
              label: "New",
              onAction: (ids) =>
                markDuplicateRequestsAsNew("on-hold-duplicate", ids),
            },
            {
              id: "new-edition",
              label: "New Edition",
              onAction: (ids) =>
                markDuplicateRequestsAsNewEdition("on-hold-duplicate", ids),
            },
            {
              id: "duplicate",
              label: "Duplicate",
              onAction: (ids) =>
                confirmDuplicateRequests("on-hold-duplicate", ids),
            },
            {
              id: "delete",
              label: "Delete",
              danger: true,
              onAction: (ids) => deleteRequests("on-hold-duplicate", ids),
            },
          ]}
        />
        <OnHoldCard
          cardId="deleted"
          cardKey="on-hold-deleted"
          title="Deleted"
          description="Deleted requests available for recreation."
          actions={[
            {
              id: "create-again",
              label: "Create Again",
              onAction: (ids) => createAgainRequests("on-hold-deleted", ids),
            },
          ]}
        />
      </div>
    </PageFrame>
  );
}
export function IncompleteProcessingPage() {
  const {
    busyCards,
    canLoadProcessingState,
    saveIncompleteAutomation,
    runIncompleteAutomation,
    pauseIncompleteAutomation,
    resumeIncompleteAutomation,
    recreateCompletedRequests,
    deleteRequests,
  } = useBookProcessing();
  const incompleteAutomationSaving = Boolean(
    busyCards["incomplete-automation-save"],
  );
  const incompleteAutomationRunning = Boolean(
    busyCards["incomplete-automation-run"],
  );
  const { data: incompleteOverviewCard, loadedOnce: incompleteOverviewLoaded } =
    useProcessingCardData({
      cardKey: "incomplete-overview",
      enabled: canLoadProcessingState,
    });
  const {
    data: incompleteAutomationCard,
    loadedOnce: incompleteAutomationLoaded,
  } = useProcessingCardData({
    cardKey: "incomplete-automation",
    enabled: canLoadProcessingState,
  });
  const summary = incompleteOverviewCard?.summary || {};
  const incompleteAutomation =
    incompleteAutomationCard?.automation || DEFAULT_AUTOMATION_CARD;
  const incompleteSync = incompleteAutomationCard?.sync || DEFAULT_SYNC_CARD;
  return (
    <PageFrame pageId="incomplete" title="Incomplete">
      <OverviewPanel
        pageId="incomplete"
        loading={!incompleteOverviewLoaded}
        stats={[
          {
            id: "incomplete",
            label: "Incomplete",
            value: summary.incomplete || 0,
          },
          {
            id: "resolved",
            label: "Updated",
            value: summary.resolved || 0,
          },
        ]}
      />
      <div className="processing-card-grid">
        <AutomationPanel
          pageId="incomplete"
          title="Automation"
          automation={incompleteAutomation}
          sync={incompleteSync}
          loading={!incompleteAutomationLoaded}
          saving={incompleteAutomationSaving}
          running={incompleteAutomationRunning}
          onSave={saveIncompleteAutomation}
          onRun={runIncompleteAutomation}
          onPause={pauseIncompleteAutomation}
          onResume={resumeIncompleteAutomation}
          className="processing-card-span-full processing-incomplete-automation-card"
        />
        <ProcessingDataCard
          pageId="incomplete"
          cardId="records"
          cardKey="incomplete-records"
          title="Incomplete"
          description="Records currently classified as incomplete."
          className="processing-inline-count-card processing-incomplete-records-card"
          bookColumnMode="split"
          countPlacement="inline-tools"
          readOnly
        />
        <ProcessingDataCard
          pageId="incomplete"
          cardId="completed"
          cardKey="incomplete-completed"
          title="Updated"
          description="Records updated by incomplete automation."
          className="processing-inline-count-card processing-incomplete-completed-card"
          busy={Boolean(busyCards["incomplete-completed"])}
          countPlacement="inline-tools"
          actions={[
            {
              id: "recreate",
              label: "Recreate Book",
              onAction: (ids) =>
                recreateCompletedRequests("incomplete-completed", ids),
            },
            {
              id: "delete",
              label: "Delete",
              danger: true,
              onAction: (ids) => deleteRequests("incomplete-completed", ids),
            },
          ]}
        />
      </div>
    </PageFrame>
  );
}
