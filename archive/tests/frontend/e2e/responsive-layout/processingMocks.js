export async function mockPropertyPagesApi(page) {
  const categories = Array.from({
    length: 6
  }, (_, index) => ({
    id: `category-${index + 1}`,
    catalog_code: `CAT-${String(index + 1).padStart(3, "0")}`,
    name: `Category ${index + 1}`,
    book_count: 20 - index,
    digital_book_count: 15 - index,
    manual_book_count: 5,
    created_at: `2026-04-${String(index + 1).padStart(2, "0")}T08:00:00Z`
  }));
  const series = Array.from({
    length: 6
  }, (_, index) => ({
    id: `series-${index + 1}`,
    name: `Series ${index + 1}`,
    book_count: 18 - index,
    digital_book_count: 14 - index,
    manual_book_count: 4,
    created_at: `2026-04-${String(index + 7).padStart(2, "0")}T08:00:00Z`
  }));
  const contributors = Array.from({
    length: 6
  }, (_, index) => ({
    id: `contributor-${index + 1}`,
    catalog_code: `WRT-${String(index + 1).padStart(3, "0")}`,
    name: `Contributor ${index + 1}`,
    book_count: 16 - index,
    digital_book_count: 12 - index,
    manual_book_count: 4,
    created_at: `2026-04-${String(index + 13).padStart(2, "0")}T08:00:00Z`
  }));
  await page.route("**/api/catalog/categories/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(categories)
    });
  });
  await page.route("**/api/catalog/series/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(series)
    });
  });
  await page.route("**/api/catalog/writers/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(contributors)
    });
  });
  await page.route("**/api/catalog/translators/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(contributors)
    });
  });
  await page.route("**/api/catalog/compilers/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(contributors)
    });
  });
  await page.route("**/api/catalog/editors/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(contributors)
    });
  });
}
export async function mockProcessingApi(page) {
  await page.addInitScript(() => {
    class MockEventSource {
      constructor() {
        this.listeners = new Map();
        this.onerror = null;
        setTimeout(() => {
          const connected = this.listeners.get("connected") || [];
          connected.forEach(listener => listener({
            data: "{}"
          }));
        }, 0);
      }
      addEventListener(type, listener) {
        const listeners = this.listeners.get(type) || [];
        listeners.push(listener);
        this.listeners.set(type, listeners);
      }
      removeEventListener(type, listener) {
        const listeners = this.listeners.get(type) || [];
        this.listeners.set(type, listeners.filter(candidate => candidate !== listener));
      }
      close() {}
    }
    window.EventSource = MockEventSource;
  });
  const rows = [{
    id: "record-1",
    recordId: "record-1",
    requestId: null,
    title: "Responsive Processing Record",
    url: "https://example.test/books/responsive-processing-record",
    displayUrl: "example.test/books/responsive-processing-record",
    displayPath: "",
    category: "Architecture",
    writer: "Ada Writer",
    translator: "Sam Translator",
    publisher: "North Press",
    status: "not_created",
    updatedAt: "2026-04-21T08:00:00Z",
    selectable: true,
    progressCheckpoint: "",
    progressSavedAt: "",
    errorMessage: "",
    isResumed: false,
    isConfirmedNotDuplicate: false,
    linkedBookId: null,
    linkedBookSlug: null,
    duplicateOfRequestId: null,
    duplicateOfRecordId: null,
    duplicateConfirmed: false
  }, {
    id: "record-2",
    recordId: "record-2",
    requestId: "request-2",
    title: "Queued Processing Record",
    url: "https://example.test/books/queued-processing-record",
    displayUrl: "example.test/books/queued-processing-record",
    displayPath: "",
    category: "History",
    writer: "Bea Writer",
    translator: "",
    publisher: "South Press",
    status: "queued",
    updatedAt: "2026-04-21T09:00:00Z",
    selectable: false,
    progressCheckpoint: "",
    progressSavedAt: "",
    errorMessage: "",
    isResumed: false,
    isConfirmedNotDuplicate: false,
    linkedBookId: null,
    linkedBookSlug: null,
    duplicateOfRequestId: null,
    duplicateOfRecordId: null,
    duplicateConfirmed: false
  }];
  const syncPayload = {
    status: "idle",
    runMode: "manual",
    message: "Ready to sync."
  };
  const automationPayload = {
    enabled: false,
    interval: "weekly",
    time: "03:00",
    saved: false,
    lastRunAt: null,
    statusMessage: ""
  };
  const summaryPayload = {
    catalog: {
      records: 24,
      notCreated: 14,
      active: 6,
      created: 3,
      onHold: 1
    },
    create: {
      requests: 1,
      queue: 1,
      processing: 0,
      created: 0
    },
    onHold: {
      paused: 0,
      failed: 0,
      duplicate: 0,
      deleted: 0
    },
    incomplete: {
      incomplete: 0,
      resolved: 0
    },
    notifications: {
      activeRequests: 1,
      createdCount: 0,
      failedCount: 0,
      duplicateCount: 0,
      latestFailedMessage: ""
    }
  };
  await page.route("**/api/processing/state/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        sync: syncPayload,
        syncStates: {
          catalog: syncPayload,
          incomplete: syncPayload
        },
        automation: {
          catalog: automationPayload,
          incomplete: automationPayload
        },
        ui: {},
        orchestration: {
          manualPipelineAdvance: false
        },
        summary: summaryPayload,
        versions: {}
      })
    });
  });
  await page.route("**/api/processing/card/**", async route => {
    const url = new URL(route.request().url());
    const card = url.searchParams.get("card") || "";
    const payloads = {
      "catalog-overview": {
        summary: {
          records: 24,
          notCreated: 14,
          active: 6,
          created: 3,
          onHold: 1
        }
      },
      "catalog-sync": {
        sync: syncPayload
      },
      "catalog-automation": {
        sync: syncPayload,
        automation: automationPayload
      }
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(payloads[card] || {})
    });
  });
  await page.route("**/api/processing/table/**", async route => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        rows,
        pagination: {
          offset: 0,
          limit: 60,
          totalCount: rows.length,
          returnedCount: rows.length,
          hasMore: false,
          nextOffset: rows.length
        },
        filters: {
          categoryOptions: ["Architecture", "History"],
          statusOptions: ["not_created", "queued"]
        }
      })
    });
  });
}
