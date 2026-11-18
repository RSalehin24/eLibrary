import { useState } from "react";
import { useBookProcessing } from "../BookProcessingStore";
import {
  DEFAULT_AUTOMATION_CARD,
  DEFAULT_SYNC_CARD,
  SYNC_RUN_MODE_CATALOG_AUTOMATION,
  SYNC_RUN_MODE_MANUAL,
  catalogActivePhase,
  catalogPhaseIsActive,
  catalogPhaseOwner,
  catalogPhaseStatus
} from "./processingPageModel";
import { OverviewPanel, PageFrame } from "./processingPagePrimitives";
import { AutomationPanel } from "./AutomationPanel";
import { CatalogSyncPanel } from "./CatalogSyncPanel";
import { ProcessingDataCard } from "./ProcessingDataCard";
import { useProcessingCardData } from "./useProcessingCardData";
export function CatalogProcessingPage() {
  const {
    busyCards,
    canLoadProcessingState,
    createRequestsForRecords,
    saveCatalogAutomation,
    runCatalogAutomation,
    pauseCatalogAutomation,
    resumeCatalogAutomation
  } = useBookProcessing();
  const {
    data: catalogOverviewCard,
    loadedOnce: catalogOverviewLoaded
  } = useProcessingCardData({
    cardKey: "catalog-overview",
    enabled: canLoadProcessingState
  });
  const {
    data: catalogSyncCard,
    loadedOnce: catalogSyncLoaded
  } = useProcessingCardData({
    cardKey: "catalog-sync",
    enabled: canLoadProcessingState
  });
  const {
    data: catalogAutomationCard,
    loadedOnce: catalogAutomationLoaded
  } = useProcessingCardData({
    cardKey: "catalog-automation",
    enabled: canLoadProcessingState
  });
  const [optimisticCatalogRuntime, setOptimisticCatalogRuntime] = useState(null);
  const catalogAutomationSaving = Boolean(busyCards["catalog-automation-save"]);
  const catalogAutomationRunning = Boolean(busyCards["catalog-automation-run"]);
  const summary = catalogOverviewCard?.summary || {};
  const catalogSync = catalogSyncCard?.sync || DEFAULT_SYNC_CARD;
  const catalogAutomation = catalogAutomationCard?.automation || DEFAULT_AUTOMATION_CARD;
  const effectiveCatalogSync = optimisticCatalogRuntime ? {
    ...catalogSync,
    status: optimisticCatalogRuntime.status,
    message: optimisticCatalogRuntime.message,
    runMode: optimisticCatalogRuntime.runMode || SYNC_RUN_MODE_MANUAL,
    phase: optimisticCatalogRuntime.phase
  } : catalogSync;
  const catalogRuntimePhase = catalogActivePhase(effectiveCatalogSync);
  const catalogRuntimeOwner = catalogRuntimePhase ? catalogPhaseOwner(effectiveCatalogSync, catalogRuntimePhase) : "";
  const catalogRuntimeBlocksModeSwitch = Boolean(catalogRuntimePhase) && catalogPhaseIsActive(catalogPhaseStatus(effectiveCatalogSync, catalogRuntimePhase));
  const manualRuntimeOwnsCatalog = catalogRuntimeBlocksModeSwitch && catalogRuntimeOwner === SYNC_RUN_MODE_MANUAL;
  const automationRuntimeOwnsCatalog = catalogRuntimeBlocksModeSwitch && catalogRuntimeOwner === SYNC_RUN_MODE_CATALOG_AUTOMATION;
  return <PageFrame pageId="catalog" title="Catalog">
      <OverviewPanel pageId="catalog" loading={!catalogOverviewLoaded} stats={[{
      id: "records",
      label: "Records",
      value: summary.records || 0
    }, {
      id: "not-created",
      label: "Remaining",
      value: summary.notCreated || 0
    }, {
      id: "active",
      label: "Creating",
      value: summary.active || 0
    }, {
      id: "created",
      label: "Books",
      value: summary.created || 0
    }, {
      id: "on-hold",
      label: "On Hold",
      value: summary.onHold || 0
    }]} />
      <div className="processing-card-grid processing-card-grid--catalog">
        <CatalogSyncPanel className="processing-catalog-sync-card" loading={!catalogSyncLoaded} sync={effectiveCatalogSync} recordCount={summary.records} blockedByExternalRuntime={automationRuntimeOwnsCatalog} onOptimisticSyncChange={setOptimisticCatalogRuntime} />
        <AutomationPanel pageId="catalog" title="Automation" automation={catalogAutomation} sync={effectiveCatalogSync} blockedByExternalRuntime={manualRuntimeOwnsCatalog} onOptimisticSyncChange={setOptimisticCatalogRuntime} recordCount={summary.records} loading={!catalogAutomationLoaded} saving={catalogAutomationSaving} running={catalogAutomationRunning} onSave={saveCatalogAutomation} onRun={runCatalogAutomation} onPause={pauseCatalogAutomation} onResume={resumeCatalogAutomation} className="processing-catalog-automation-card" />
      </div>
      <ProcessingDataCard pageId="catalog" cardId="records" cardKey="catalog-records" title="Book Records" description="Synced catalog records ready for book creation." busy={Boolean(busyCards["catalog-records"])} className="processing-inline-count-card processing-catalog-card processing-catalog-records-card" bookColumnMode="split" showDetailsColumn={false} countPlacement="inline-tools" actions={[{
      id: "create",
      label: "Create Book",
      onAction: ids => createRequestsForRecords(ids)
    }]} />
    </PageFrame>;
}
