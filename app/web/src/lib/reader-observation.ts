const OBSERVATION_INTERVAL_MS = 200;

export function observeReaderDocument(document: Document, capture: () => void) {
  // WebKit suppresses callbacks inside script-disabled chapter frames.
  // Observe from the parent realm while keeping authored scripts disabled.
  const sample = () => { if (document.documentElement.isConnected && window.document.visibilityState === "visible") capture(); };
  const timer = window.setInterval(sample, OBSERVATION_INTERVAL_MS);
  sample();
  return () => window.clearInterval(timer);
}
