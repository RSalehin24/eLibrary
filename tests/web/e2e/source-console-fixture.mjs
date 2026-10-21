import { expect } from "./fixtures.mjs";

export async function useIdleDiscoveryOptions(page) {
  const response = await page.request.get("/api/v1/manage/sources/discovery/?catalog_scope=all");
  expect(response.status()).toBe(200);
  const options = await response.json();
  await page.route("**/api/v1/manage/sources/discovery/?*", route => route.request().method() === "GET"
    ? route.fulfill({ json: { ...options, active_operation_id: null, latest_operation_id: null } })
    : route.continue());
}
