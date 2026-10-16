export function installLabObservers() {
  const metrics = { lcp_ms: null, cls: 0, max_interaction_duration_ms: null, supported: [] };
  const layout = { first: null, last: null, score: 0 };
  const handlers = {
    "largest-contentful-paint": (entry) => { metrics.lcp_ms = entry.startTime; },
    "layout-shift": (entry) => {
      if (entry.hadRecentInput) return;
      if (layout.first === null || entry.startTime - layout.last >= 1000 || entry.startTime - layout.first >= 5000) {
        layout.first = entry.startTime;
        layout.score = 0;
      }
      layout.last = entry.startTime;
      layout.score += entry.value;
      metrics.cls = Math.max(metrics.cls, layout.score);
    },
    event: (entry) => {
      if (entry.interactionId) metrics.max_interaction_duration_ms = Math.max(metrics.max_interaction_duration_ms ?? 0, entry.duration);
    },
  };
  for (const [type, handler] of Object.entries(handlers)) {
    if (!PerformanceObserver.supportedEntryTypes.includes(type)) continue;
    new PerformanceObserver((list) => list.getEntries().forEach(handler)).observe({ type, buffered: true, ...(type === "event" ? { durationThreshold: 16 } : {}) });
    metrics.supported.push(type);
  }
  window.libraryLabMetrics = metrics;
}
