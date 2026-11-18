import {
  getContributorGroups,
  getContributorRoleLabel,
  getPrimaryContributorGroup,
} from "../../utils/bookPresentation";

export function openManagedPreviewWindow(previewUrl, target) {
  const openedWindow = window.open("", target);
  if (!openedWindow) {
    return null;
  }

  try {
    if (openedWindow.location.href !== previewUrl) {
      openedWindow.location.replace(previewUrl);
    }
  } catch {
    openedWindow.location = previewUrl;
  }

  return openedWindow;
}

function normalizeIdentityLabel(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

export function normalizeFrontMatterEntries(entries, bookIdValue) {
  if (!entries?.length) {
    return [];
  }

  let replacedIdentity = false;
  const seen = new Set();

  return entries.reduce((normalizedEntries, entry) => {
    const normalizedLabel = normalizeIdentityLabel(entry.label);
    const normalizedKey = normalizeIdentityLabel(entry.key);
    const isIdentityEntry =
      ["unique id", "book id", "catalog code", "catalog id", "id"].includes(
        normalizedLabel,
      ) ||
      ["unique id", "book id", "catalog code", "catalog id", "id"].includes(
        normalizedKey,
      );

    if (isIdentityEntry) {
      if (!replacedIdentity) {
        const normalizedEntry = {
          ...entry,
          key: "book_id",
          label: "Book ID",
          value: bookIdValue,
        };
        const dedupeKey = `${normalizeIdentityLabel(normalizedEntry.key)}::${normalizeIdentityLabel(normalizedEntry.value)}`;
        if (!seen.has(dedupeKey)) {
          seen.add(dedupeKey);
          normalizedEntries.push(normalizedEntry);
        }
        replacedIdentity = true;
      }
      return normalizedEntries;
    }

    const dedupeKey = `${normalizedKey || normalizedLabel}::${normalizeIdentityLabel(entry.value)}`;
    if (seen.has(dedupeKey)) {
      return normalizedEntries;
    }
    seen.add(dedupeKey);
    normalizedEntries.push(entry);
    return normalizedEntries;
  }, []);
}

function appendExtractedEntry(entries, seen, entry) {
  const value = String(entry.value || "").trim();
  if (!value) {
    return;
  }
  const label = String(entry.label || entry.key || "Detail").trim();
  const dedupeKey = `${normalizeIdentityLabel(label)}::${normalizeIdentityLabel(value)}`;
  if (seen.has(dedupeKey)) {
    return;
  }
  seen.add(dedupeKey);
  entries.push({
    ...entry,
    label,
    value,
  });
}

function extractedContributorLabel(role) {
  if (role === "author") {
    return "Author";
  }
  return getContributorRoleLabel(role) || "Contributor";
}

export function buildExtractedDetailEntries(book, frontMatter) {
  if (!book) {
    return [];
  }

  const entries = [];
  const seen = new Set();

  getContributorGroups(book).forEach((group) => {
    group.names.forEach((name) => {
      appendExtractedEntry(entries, seen, {
        key: `contributor_${group.role}`,
        label: extractedContributorLabel(group.role),
        value: name,
        source: "contributor",
      });
    });
  });

  (book.series || []).forEach((name) => {
    appendExtractedEntry(entries, seen, {
      key: "series",
      label: "Series",
      value: name,
      source: "series",
    });
  });

  (book.categories || []).forEach((name) => {
    appendExtractedEntry(entries, seen, {
      key: "category",
      label: "Category",
      value: name,
      source: "category",
    });
  });

  (frontMatter || []).forEach((entry) => {
    appendExtractedEntry(entries, seen, {
      ...entry,
      source: "front_matter",
    });
  });

  return entries;
}

export function waitForUiFrame() {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(resolve);
    });
  });
}

export function waitForMinimumLoader(startedAt, minimumMs = 320) {
  const elapsed = Date.now() - startedAt;
  const remaining = minimumMs - elapsed;
  if (remaining <= 0) {
    return Promise.resolve();
  }
  return new Promise((resolve) => window.setTimeout(resolve, remaining));
}

export function buildSourceRecords(book) {
  if (!book) {
    return [];
  }

  return book.source_records?.length
    ? book.source_records
    : (book.source_urls || []).map((url) => ({
        url,
        display_url: decodeURIComponent(url),
        display_path: decodeURIComponent(url).replace(
          /^https?:\/\/[^/]+\//,
          "",
        ),
        source_title: "",
        site: "",
        is_primary: false,
      }));
}

export function buildBookDetailView(book, readerState) {
  if (!book) {
    return {
      bookIdValue: "Pending",
      downloadableAssets: [],
      epubAsset: null,
      extractedEntries: [],
      frontMatter: [],
      hasActiveProcessing: false,
      hasDedication: false,
      hasFailedProcessing: false,
      hasFrontMatter: false,
      hasToc: false,
      latestProcessingJob: null,
      primaryContributorGroup: null,
      processingBody: "",
      processingHeading: "Processing book",
      progressPercent: 0,
      sourceRecords: [],
      supportingContributorGroups: [],
    };
  }

  const contributorGroups = getContributorGroups(book);
  const primaryContributorGroup = getPrimaryContributorGroup(book);
  const supportingContributorGroups = contributorGroups.filter(
    (group) => group.role !== primaryContributorGroup?.role,
  );
  const bookIdValue = book.catalog_code || "Pending";
  const frontMatter = normalizeFrontMatterEntries(
    book.front_matter || [],
    bookIdValue,
  );
  const extractedEntries = buildExtractedDetailEntries(book, frontMatter);
  const hasFrontMatter = Boolean(
    extractedEntries.length || book.book_info_html?.trim(),
  );
  const hasDedication = Boolean(book.dedication_html?.trim());
  const hasToc = Boolean(book.toc?.length);
  const progressPercent = Math.max(
    0,
    Math.min(100, Math.round(Number(readerState.progress_percent) || 0)),
  );
  const latestProcessingJob = book.latest_processing_job || null;
  const hasActiveProcessing = Boolean(
    latestProcessingJob &&
    ["queued", "processing"].includes(latestProcessingJob.status),
  );
  const hasFailedProcessing = latestProcessingJob?.status === "failed";
  const epubAsset = (book.assets || []).find(
    (asset) => asset.asset_type === "epub",
  );
  const downloadableAssets = (book.assets || []).filter(
    (asset) => asset.download_url,
  );
  const processingHeading =
    latestProcessingJob?.job_type === "reprocess"
      ? "Regenerating book"
      : "Processing book";
  const processingBody = hasFailedProcessing
    ? latestProcessingJob?.last_error || "The latest processing job failed."
    : hasActiveProcessing
      ? "New book files are being prepared. This page refreshes automatically while the job is running."
      : "";

  return {
    bookIdValue,
    downloadableAssets,
    epubAsset,
    extractedEntries,
    frontMatter,
    hasActiveProcessing,
    hasDedication,
    hasFailedProcessing,
    hasFrontMatter,
    hasToc,
    latestProcessingJob,
    primaryContributorGroup,
    processingBody,
    processingHeading,
    progressPercent,
    sourceRecords: buildSourceRecords(book),
    supportingContributorGroups,
  };
}
