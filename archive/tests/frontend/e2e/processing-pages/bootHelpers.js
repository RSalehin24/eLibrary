import { mockAuthenticatedSession } from "./fixtures.js";
import { mockProcessingApi } from "./processingApiMock.js";
export async function boot(page, path, state, options = {}) {
  await mockAuthenticatedSession(page);
  const processingApi = await mockProcessingApi(page, state, options);
  await page.goto(path);
  if (options.eventSourceMode !== "unsupported") {
    await page.waitForFunction(() => window.__processingStreamSourceCount > 0);
    processingApi.startStream();
  }
  return processingApi;
}
export function row(page, pageId, cardId, id) {
  return page.getByTestId(`${pageId}-${cardId}-row-${id}`);
}
export function card(page, pageId, cardId) {
  return page.getByTestId(`${pageId}-${cardId}-card`);
}
