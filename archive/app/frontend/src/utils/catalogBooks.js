export const CATALOG_TABLE_BATCH_SIZE = 60;
export const CATALOG_TABLE_PREFETCH_TRIGGER = 30;

const defaultPagination = {
  page: 1,
  limit: CATALOG_TABLE_BATCH_SIZE,
  total_count: 0,
  page_count: 1,
  has_previous: false,
  has_next: false,
};

export function normalizeCatalogListPayload(payload) {
  if (Array.isArray(payload)) {
    return {
      entries: payload,
      pagination: {
        ...defaultPagination,
        total_count: payload.length,
      },
    };
  }

  return {
    entries: payload?.entries || [],
    pagination: {
      ...defaultPagination,
      ...(payload?.pagination || {}),
    },
  };
}

export const normalizeBookPayload = normalizeCatalogListPayload;
