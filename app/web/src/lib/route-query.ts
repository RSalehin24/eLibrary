import { notFound } from "next/navigation";

export type RouteQuery = Record<string, string | string[] | undefined>;

export function queryValue(parameters: RouteQuery, name: string) {
  const value = parameters[name];
  if (value === undefined) return "";
  if (typeof value !== "string") notFound();
  return value;
}

export function routePageNumber(parameters: RouteQuery) {
  const raw = queryValue(parameters, "page") || "1";
  if (!/^[0-9]+$/.test(raw)) notFound();
  const page = Number(raw);
  if (!Number.isSafeInteger(page) || page < 1) notFound();
  return page;
}

export function catalogPageNumber(parameters: RouteQuery) {
  const page = routePageNumber(parameters);
  if (page > 10000) notFound();
  return page;
}
