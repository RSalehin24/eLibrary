import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { OperationAccepted, SourceBulkCommand, SourceBulkResult, SourceDiscoveryCommand, SourceIssue, SourceProcessingCommand, SourceResolution } from "./types";

export const processSource = (id: string, values: SourceProcessingCommand) => apiMutation<OperationAccepted>(`manage/sources/${id}/process/`, { method: "POST", body: JSON.stringify(values) });
export const readSourceIssue = (id: string, signal?: AbortSignal) => apiRequest<SourceIssue>(`manage/jobs/${id}/source-issue/`, { signal });
export const resolveSourceIssue = (id: string, values: SourceResolution) => apiMutation<OperationAccepted>(`manage/jobs/${id}/source-issue/`, { method: "POST", body: JSON.stringify(values) });
export const processSourceSelection = (values: SourceBulkCommand) => apiMutation<SourceBulkResult>("manage/sources/process-selection/", { method: "POST", body: JSON.stringify(values) });
export const discoverSources = (values: SourceDiscoveryCommand) => apiMutation<OperationAccepted>("manage/sources/discovery/", { method: "POST", body: JSON.stringify(values) });
