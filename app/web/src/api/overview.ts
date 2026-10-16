import { apiRequest } from "./http";
import type { ManagementOverview, OverviewWork } from "./types";

export const readManagementOverview = (signal?: AbortSignal) => apiRequest<ManagementOverview>("manage/overview/", { signal });
export const readOverviewWork = (signal?: AbortSignal) => apiRequest<OverviewWork>("manage/overview/work/", { signal });
