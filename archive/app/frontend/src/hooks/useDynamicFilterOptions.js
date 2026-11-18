import { useState, useEffect, useRef } from "react";
import { catalogFetch } from "../api/catalog";

export function useDynamicFilterOptions(filters, setFilters) {
  const [authors, setAuthors] = useState([]);
  const [seriesList, setSeriesList] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);

  // Use a ref to track the last filters object we processed to avoid redundant fetch/reset loops
  const lastProcessedRef = useRef(null);

  useEffect(() => {
    let active = true;

    async function loadOptions() {
      setLoading(true);
      try {
        const recordType = filters.record_type || "all";
        const author = filters.author || "";
        const series = filters.series || "";
        const category = filters.category || "";

        // To prevent infinite loops, check if we've already fetched/processed these exact filters
        const cacheKey = `${recordType}:${author}:${series}:${category}`;
        if (lastProcessedRef.current === cacheKey) {
          setLoading(false);
          return;
        }

        // Fetch writers (filtered by series, category, recordType - NOT author)
        // Fetch series (filtered by author, category, recordType - NOT series)
        // Fetch categories (filtered by author, series, recordType - NOT category)
        const [authorsData, seriesData, categoriesData] = await Promise.all([
          catalogFetch(`/catalog/writers/?record_type=${recordType}&series=${encodeURIComponent(series)}&category=${encodeURIComponent(category)}&sort=name`),
          catalogFetch(`/catalog/series/?record_type=${recordType}&author=${encodeURIComponent(author)}&category=${encodeURIComponent(category)}&sort=name`),
          catalogFetch(`/catalog/categories/?record_type=${recordType}&author=${encodeURIComponent(author)}&series=${encodeURIComponent(series)}&sort=name`),
        ]);

        if (active) {
          const newAuthors = authorsData.map(item => item.name);
          const newSeries = seriesData.map(item => item.name);
          const newCategories = categoriesData.map(item => item.name);

          setAuthors(newAuthors);
          setSeriesList(newSeries);
          setCategories(newCategories);

          // Check if current values are still valid, if not, reset them
          let filtersChanged = false;
          const nextFilters = { ...filters };

          if (author && !newAuthors.includes(author)) {
            nextFilters.author = "";
            filtersChanged = true;
          }
          if (series && !newSeries.includes(series)) {
            nextFilters.series = "";
            filtersChanged = true;
          }
          if (category && !newCategories.includes(category)) {
            nextFilters.category = "";
            filtersChanged = true;
          }

          lastProcessedRef.current = `${recordType}:${nextFilters.author}:${nextFilters.series}:${nextFilters.category}`;

          if (filtersChanged) {
            setFilters(nextFilters);
          }
        }
      } catch (err) {
        console.error("Failed to load dynamic filter options:", err);
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    loadOptions();

    return () => {
      active = false;
    };
  }, [filters.author, filters.series, filters.category, filters.record_type, setFilters]);

  return { authors, seriesList, categories, loading };
}
