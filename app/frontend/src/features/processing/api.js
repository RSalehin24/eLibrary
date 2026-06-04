import { apiFetch, resolveApiUrl } from "../../api/client";

export function processingFetch(path, options) {
  return apiFetch(path, options);
}

export function resolveProcessingStreamUrl(path) {
  return resolveApiUrl(path);
}

export function getReprocessJobs() {
  return apiFetch("/ingestion/jobs/?job_type=reprocess&limit=200");
}

export function getReprocessSummary() {
  return apiFetch("/ingestion/jobs/reprocess/summary/");
}

export function stopReprocessJob(id) {
  return apiFetch(`/ingestion/jobs/${id}/stop/`, { method: "POST" });
}

export function deleteReprocessJob(id) {
  return apiFetch(`/ingestion/jobs/${id}/`, { method: "DELETE" });
}

export function resumeReprocessJob(id) {
  return apiFetch(`/ingestion/jobs/${id}/resume/`, { method: "POST" });
}
