import { iso } from "./fixtures.js";
import { applyRequestTimeouts } from "./stateRows.js";
export function advancePipelineState(state) {
  applyRequestTimeouts(state);
  for (const item of state.requests) {
    if (item.state === "initial") {
      item.state = "queued";
    } else if (item.state === "queued") {
      item.state = "processing";
    } else if (item.state === "processing") {
      if (item.pipelineOutcome === "failed") {
        item.state = "failed";
        item.errorMessage = item.errorMessage || "Pipeline failed after retries.";
      } else if (item.pipelineOutcome === "duplicate") {
        item.state = "duplicate";
      } else {
        item.state = "created";
        item.linkedBookId = item.linkedBookId || `linked-${item.bookRecordId}`;
        item.linkedBookSlug = item.linkedBookSlug || `${item.bookRecordId}-book`;
        const recordItem = state.records.find(record => record.id === item.bookRecordId);
        if (recordItem) {
          recordItem.linkedBookId = item.linkedBookId;
          recordItem.linkedBookSlug = item.linkedBookSlug;
        }
      }
    }
    item.updatedAt = iso(200 + state.requests.indexOf(item));
  }
  applyRequestTimeouts(state);
}
