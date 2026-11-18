export const seedData = {
  accessUser: {
    email: "access-manager@e2e.local",
    name: "E2E Access Manager",
  },
  books: {
    homePrimary: {
      title: "E2E Home Library Book",
      slug: "e2e-home-library-book",
    },
    homeSecondary: {
      title: "E2E Search Companion Book",
      slug: "e2e-search-companion-book",
    },
    detail: {
      title: "E2E Detail Book",
      slug: "e2e-detail-book",
      sourceUrl: "https://www.example.com/books/e2e-detail-book/",
    },
    preview: {
      title: "E2E Preview Book",
      slug: "e2e-preview-book",
    },
    access: {
      title: "E2E Access Grant Book",
      slug: "e2e-access-grant-book",
    },
    incomplete: {
      title: "E2E Incomplete Catalog Book",
      slug: "e2e-incomplete-catalog-book",
    },
  },
  catalogFilters: {
    category: "E2E Fiction",
    series: "E2E Starter Series",
    writer: "E2E Writer",
  },
  submissions: {
    alpha: "E2E Alpha Submission",
    beta: "E2E Beta Submission",
    userPending: "E2E User Pending Submission",
    userProcessing: "E2E User Processing Submission",
    userStopped: "E2E User Stopped Submission",
    userDeleted: "E2E User Deleted Submission",
    userFailed: "E2E User Failed Submission",
    automationPending: "E2E Automation Pending Submission",
    automationReady: "E2E Automation Ready Submission",
    automationProcessing: "E2E Automation Processing Submission",
    automationQueued: "E2E Automation Queued Submission",
    automationStopped: "E2E Automation Stopped Submission",
    automationDeleted: "E2E Automation Deleted Submission",
    curationReady: "E2E Curation Ready Submission",
    curationProcessing: "E2E Curation Processing Submission",
    curationQueued: "E2E Curation Queued Submission",
    curationStopped: "E2E Curation Stopped Submission",
    curationDeleted: "E2E Curation Deleted Submission",
    duplicateReview: "E2E Duplicate Review Submission",
  },
  catalogEntries: {
    alpha: "000 E2E Alpha Catalog Book",
    beta: "001 E2E Beta Catalog Book",
  },
  processing: {
    failedLogMessage: "Seeded failed job log entry.",
    scheduledRunActiveSummary: "7 create",
    scheduledRunFailedSummary: "2 create",
  },
  bookmark: {
    label: "Seeded Bookmark",
  },
};
