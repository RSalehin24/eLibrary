export function toQueryString(params) {
  const searchParams = new URLSearchParams();

  Object.entries(params || {}).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }

    const stringValue = String(value).trim();
    if (!stringValue) {
      return;
    }

    searchParams.set(key, stringValue);
  });

  const queryString = searchParams.toString();
  return queryString ? `?${queryString}` : "";
}

export function cleanQueryParams(params) {
  return Object.fromEntries(
    Object.entries(params || {}).filter(([, value]) => value !== undefined && value !== null && String(value).trim())
  );
}

export function filtersFromSearchParams(defaultFilters, searchParams) {
  const nextFilters = { ...(defaultFilters || {}) };

  Object.keys(defaultFilters || {}).forEach((key) => {
    const value = searchParams.get(key);
    if (value !== null) {
      nextFilters[key] = value;
    }
  });

  return nextFilters;
}
