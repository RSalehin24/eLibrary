import { expect, test } from "./support/playwright";

function nowIso() {
  return new Date(Date.UTC(2026, 3, 17, 9, 0, 0)).toISOString();
}

async function mockAuthenticatedSession(page) {
  await page.route("**/api/auth/session/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        authenticated: true,
        user: {
          id: "create-processing-user",
          email: "create-processing@example.com",
          full_name: "Create Processing",
          is_superuser: true,
          capabilities: ["processing:manage"],
          totp_setup_required: false,
        },
      }),
    });
  });
  await page.route("**/api/csrf/", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ detail: "ok" }),
    });
  });
}

async function mockCreateProcessingApi(page) {
  const timestamp = nowIso();
  const versions = {
    "catalog-overview": 0,
    "catalog-sync": 0,
    "catalog-automation": 0,
    "catalog-records": 0,
    "create-overview": 0,
    "create-requests": 0,
    "create-queue": 0,
    "create-processing": 0,
    "create-created": 0,
    "on-hold-overview": 0,
    "on-hold-paused": 0,
    "on-hold-failed": 0,
    "on-hold-duplicate": 0,
    "on-hold-deleted": 0,
    "incomplete-overview": 0,
    "incomplete-automation": 0,
    "incomplete-records": 0,
    "incomplete-completed": 0,
  };
  const state = {
    records: [
      {
        id: "create-page-record",
        name: "Create Page Request",
        url: "https://example.test/create-page-request",
        category: "Regression",
        writer: "Create Writer",
        translator: null,
        composer: null,
        publisher: "Create Press",
        createdAt: timestamp,
        updatedAt: timestamp,
        bookCreationState: "initial",
        selectable: false,
        latestRequestId: "create-page-request",
      },
    ],
    requests: [
      {
        id: "create-page-request",
        bookRecordId: "create-page-record",
        state: "initial",
        createdAt: timestamp,
        updatedAt: timestamp,
        progress: null,
        errorMessage: null,
        isResumed: false,
        isConfirmedNotDuplicate: false,
        duplicateOfRequestId: null,
        duplicateOfRecordId: null,
        duplicateConfirmed: false,
        linkedBookId: null,
      },
    ],
    sync: {
      status: "idle",
      progress: null,
      fetchedCount: 0,
      skippedCount: 0,
      updatedCount: 0,
      appendedCount: 0,
      message: "Ready to sync.",
      remotePages: [],
      pageIndex: 0,
    },
    automation: {
      catalog: {
        enabled: false,
        interval: "weekly",
        time: "03:00",
        saved: false,
        lastRunAt: null,
        statusMessage: "",
      },
      incomplete: {
        enabled: false,
        interval: "weekly",
        time: "03:00",
        saved: false,
        lastRunAt: null,
        statusMessage: "",
      },
    },
    ui: {
      pipelineDelayMs: 2_000,
    },
  };

  await page.addInitScript(() => {
    class MockEventSource {
      constructor() {
        this.listeners = new Map();
        setTimeout(() => {
          const listeners = this.listeners.get("connected") || [];
          const event = { data: JSON.stringify({}) };
          listeners.forEach((listener) => listener(event));
        }, 0);
      }

      addEventListener(type, listener) {
        const listeners = this.listeners.get(type) || [];
        listeners.push(listener);
        this.listeners.set(type, listeners);
      }

      removeEventListener(type, listener) {
        const listeners = this.listeners.get(type) || [];
        this.listeners.set(
          type,
          listeners.filter((candidate) => candidate !== listener),
        );
      }

      close() {}
    }

    window.EventSource = MockEventSource;
  });

  async function fulfillState(route) {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        summary: {
          catalog: {
            records: 1,
            notCreated: 0,
            active: 1,
            created: 0,
            onHold: 0,
          },
          notifications: {
            pipelineActive: true,
            activeSync: false,
            hasActiveWork: true,
          },
          create: {
            requests: 1,
            queue: 0,
            processing: 0,
            created: 0,
          },
          onHold: {
            paused: 0,
            failed: 0,
            duplicate: 0,
            deleted: 0,
          },
          incomplete: {
            incomplete: 0,
            completed: 0,
          },
        },
        sync: state.sync,
        syncStates: {
          catalog: state.sync,
          incomplete: state.sync,
        },
        automation: state.automation,
        versions,
      }),
    });
  }

  await page.route("**/api/processing/state/**", fulfillState);
  await page.route("**/api/processing/table/**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        card: "create-requests",
        version: versions["create-requests"],
        rows: [
          {
            id: "create-page-request",
            title: "Create Page Request",
            url: "https://example.test/create-page-request",
            displayUrl: "https://example.test/create-page-request",
            category: "Regression",
            writer: "Create Writer",
            translator: "",
            composer: "",
            publisher: "Create Press",
            status: "initial",
            updatedAt: timestamp,
            linkedBookSlug: null,
            selectable: false,
          },
        ],
        pagination: {
          offset: 0,
          limit: 60,
          totalCount: 1,
          hasMore: false,
        },
        filters: {
          categoryOptions: ["Regression"],
          statusOptions: ["initial"],
        },
      }),
    });
  });
}

test.describe("Create processing page", () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test("the /create route renders the new processing request cards", async ({
    page,
  }) => {
    await mockAuthenticatedSession(page);
    await mockCreateProcessingApi(page);

    await page.goto("/create");

    await expect(
      page.getByRole("heading", { level: 1, name: "Create", exact: true }),
    ).toBeVisible();
    await expect(page.getByTestId("create-requests-card")).toBeVisible();
    await expect(page.getByTestId("create-requests-row-create-page-request")).toBeVisible();
    await expect(page.getByText("Create EPUB")).toHaveCount(0);
  });
});
