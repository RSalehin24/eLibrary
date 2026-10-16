import { apiRequest } from "./http";
import { apiMutation } from "./mutation";
import type { AutomationCreate, AutomationRuns, Automations, AutomationUpdate, SourceAutomation } from "./types";

export const readAutomations = (query: string, signal?: AbortSignal) => apiRequest<Automations>(`manage/automations/?${query}`, { signal });
export const readAutomationRuns = (id: string, query: string, signal?: AbortSignal) => apiRequest<AutomationRuns>(`manage/automations/${id}/runs/?${query}`, { signal });
export const createAutomation = (values: AutomationCreate) => apiMutation<SourceAutomation>("manage/automations/", { method: "POST", body: JSON.stringify(values) });
export const updateAutomation = (id: string, values: AutomationUpdate) => apiMutation<SourceAutomation>(`manage/automations/${id}/`, { method: "PATCH", body: JSON.stringify(values) });
