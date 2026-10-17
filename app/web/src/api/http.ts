type ErrorDetails = { code?: string; detail?: string; fieldErrors?: Record<string, string[]> };

export class APIError extends Error {
  readonly code: string;
  readonly detail: string;
  readonly fieldErrors: Record<string, string[]>;

  constructor(message: string, readonly status: number, details: ErrorDetails = {}) {
    super(message);
    this.code = details.code ?? "request_failed";
    this.detail = details.detail ?? "";
    this.fieldErrors = details.fieldErrors ?? {};
  }
}

function errorFields(value: unknown): Record<string, string[]> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {};
  return Object.fromEntries(Object.entries(value).map(([field, errors]) => [field,
    Array.isArray(errors) ? errors.filter((error): error is string => typeof error === "string") : typeof errors === "string" ? [errors] : [],
  ]));
}

async function responseError(response: Response) {
  const message = "তথ্যটি এখন পাওয়া যাচ্ছে না। আবার চেষ্টা করুন।";
  if (!response.headers.get("content-type")?.includes("application/json")) return new APIError(message, response.status);
  const payload: unknown = await response.json();
  if (!payload || typeof payload !== "object") return new APIError(message, response.status);
  return new APIError(message, response.status, {
    code: "code" in payload && typeof payload.code === "string" ? payload.code : undefined,
    detail: "detail" in payload && typeof payload.detail === "string" ? payload.detail : undefined,
    fieldErrors: errorFields("field_errors" in payload ? payload.field_errors : undefined),
  });
}

export async function readJSON<ResponseType>(response: Response): Promise<ResponseType> {
  if (!response.ok) {
    throw await responseError(response);
  }
  return response.json() as Promise<ResponseType>;
}

export async function apiRequest<ResponseType>(path: string, options?: RequestInit) {
  const response = await fetch(`/api/v1/${path}`, {
    ...options, credentials: "same-origin", cache: "no-store",
  });
  return readJSON<ResponseType>(response);
}

export async function apiEmptyResponse(path: string, options: RequestInit) {
  const response = await fetch(`/api/v1/${path}`, { ...options, credentials: "same-origin", cache: "no-store" });
  if (!response.ok) throw await responseError(response);
  if (response.status !== 204) throw new APIError("অনুরোধের ফল পাওয়া যায়নি।", response.status);
}

export const apiDelete = apiEmptyResponse;
