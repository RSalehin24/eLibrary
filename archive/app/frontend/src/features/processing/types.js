export const BOOK_CREATION_REQUEST_STATES = [
  "initial",
  "queued",
  "processing",
  "created",
  "paused",
  "failed",
  "duplicate",
  "deleted",
];

export const BOOK_CREATION_STATES = [
  "not_created",
  ...BOOK_CREATION_REQUEST_STATES,
];

export const TERMINAL_REQUEST_STATES = [
  "created",
  "failed",
  "duplicate",
  "deleted",
];

export const ACTIVE_REQUEST_STATES = ["initial", "queued", "processing"];
export const HOLDING_REQUEST_STATES = ["paused"];

export const REQUEST_STATE_LABELS = {
  not_created: "Not created",
  initial: "Initial",
  queued: "Queued",
  processing: "Processing",
  created: "Created",
  paused: "Paused",
  failed: "Failed",
  duplicate: "Duplicate",
  deleted: "Deleted",
};

/**
 * @typedef {"not_created" | "initial" | "queued" | "processing" | "created" | "paused" | "failed" | "duplicate" | "deleted"} BookCreationState
 */

/**
 * @typedef {"initial" | "queued" | "processing" | "created" | "paused" | "failed" | "duplicate" | "deleted"} BookCreationRequestState
 */

/**
 * @typedef {Object} RequestProgress
 * @property {string} savedAt
 * @property {string} checkpoint
 * @property {unknown} savedData
 */

/**
 * @typedef {Object} BookRecord
 * @property {string} id
 * @property {string} name
 * @property {string} url
 * @property {string | undefined} displayUrl
 * @property {string | undefined} displayPath
 * @property {string} category
 * @property {string | null} writer
 * @property {string | null} translator
 * @property {string | null} composer
 * @property {string | undefined} publisher
 * @property {string} createdAt
 * @property {string} updatedAt
 * @property {BookCreationState} bookCreationState
 */

/**
 * @typedef {Object} BookCreationRequest
 * @property {string} id
 * @property {string} bookRecordId
 * @property {BookCreationRequestState} state
 * @property {string} createdAt
 * @property {string} updatedAt
 * @property {RequestProgress | null | undefined} progress
 * @property {string | null | undefined} errorMessage
 * @property {boolean | undefined} isResumed
 * @property {boolean | undefined} isConfirmedNotDuplicate
 * @property {string | null | undefined} duplicateOfRequestId
 * @property {string | null | undefined} duplicateOfRecordId
 */
