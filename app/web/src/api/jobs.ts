import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { BackgroundJob, BackgroundJobCollection, BackgroundJobDetail, JobControl, OperationAccepted, ProcessingAsset } from "./types";

export const readJobs = (query: string, signal?: AbortSignal) => apiRequest<BackgroundJobCollection>(`manage/jobs/?${query}`, { signal });
export const readJob = (identifier: string, signal?: AbortSignal) => apiRequest<BackgroundJobDetail>(`manage/jobs/${identifier}/`, { signal });
export const readProcessingAssets = (slug: string, signal?: AbortSignal) => apiRequest<ProcessingAsset[]>(`manage/books/${encodeURIComponent(slug)}/assets/`, { signal });
export const controlJob = (job: BackgroundJob, action: JobControl["action"]) => apiMutation<OperationAccepted>(`manage/jobs/${job.id}/`, { method: "POST", body: JSON.stringify({ action, expected_updated_at: job.updated_at }) });
export const prepareAsset = (asset: ProcessingAsset, operationId: string) => apiMutation<OperationAccepted>(`manage/assets/${asset.id}/prepare/`, { method: "POST", body: JSON.stringify({ operation_id: operationId, expected_updated_at: asset.updated_at }) });
