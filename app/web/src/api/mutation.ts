import { APIError, apiEmptyResponse, apiRequest } from "./http";
import type { WorkspaceSession } from "./types";

async function mutationOptions(options: RequestInit) {
  const session = await apiRequest<WorkspaceSession>("auth/session/");
  const headers = new Headers(options.headers);
  headers.set("X-CSRFToken", session.csrf_token);
  if (options.body instanceof FormData) headers.delete("Content-Type");
  else headers.set("Content-Type", "application/json");
  return { ...options, headers };
}

export async function apiMutation<ResponseType>(path: string, options: RequestInit) {
  try { return await apiRequest<ResponseType>(path, await mutationOptions(options)); }
  catch (error) {
    if (!csrfRejected(error)) throw error;
    return apiRequest<ResponseType>(path, await mutationOptions(options));
  }
}

export async function emptyMutation(path: string, options: RequestInit) {
  try { return await apiEmptyResponse(path, await mutationOptions(options)); }
  catch (error) {
    if (!csrfRejected(error)) throw error;
    return apiEmptyResponse(path, await mutationOptions(options));
  }
}

function csrfRejected(error: unknown) {
  return error instanceof APIError && error.status === 403 && error.code === "csrf_failed";
}

export const deleteMutation = (path: string) => emptyMutation(path, { method: "DELETE" });
