import "server-only";
import { cookies } from "next/headers";
import { readJSON } from "./http";

const apiOrigin = process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000";
const forwardedProtocol = new URL(process.env.PUBLIC_SITE_URL ?? "http://127.0.0.1:3000").protocol.slice(0, -1);

export async function publicRequest<ResponseType>(path: string) {
  const response = await fetch(`${apiOrigin}/api/v1/${path}`, {
    cache: "no-store", headers: { "X-Forwarded-Proto": forwardedProtocol }, signal: AbortSignal.timeout(10_000),
  });
  return readJSON<ResponseType>(response);
}

export async function sessionRequest<ResponseType>(path: string) {
  const cookieHeader = (await cookies()).toString();
  const response = await fetch(`${apiOrigin}/api/v1/${path}`, {
    cache: "no-store", headers: { Cookie: cookieHeader, "X-Forwarded-Proto": forwardedProtocol },
    signal: AbortSignal.timeout(10_000),
  });
  return readJSON<ResponseType>(response);
}
