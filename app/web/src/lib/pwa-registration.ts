import { useEffect, useRef, useState } from "react";

export function useServiceWorker() {
  const [waiting, setWaiting] = useState<ServiceWorker | null>(null);
  const [failed, setFailed] = useState(false);
  const accepted = useRef(false);
  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    let registration: ServiceWorkerRegistration | undefined;
    let disposed = false;
    const installed = () => { setWaiting(navigator.serviceWorker.controller ? registration?.waiting ?? null : null); };
    const changed = () => { if (accepted.current) window.location.reload(); };
    const update = () => { const worker = registration?.installing; worker?.addEventListener("statechange", installed); };
    const refresh = () => { if (document.visibilityState === "visible") void registration?.update().catch(() => setFailed(true)); };
    navigator.serviceWorker.addEventListener("controllerchange", changed);
    document.addEventListener("visibilitychange", refresh);
    navigator.serviceWorker.register("/sw.js", { scope: "/", type: "module", updateViaCache: "none" }).then((result) => { if (disposed) return; registration = result; installed(); result.addEventListener("updatefound", update); update(); }).catch(() => setFailed(true));
    return () => { disposed = true; registration?.removeEventListener("updatefound", update); navigator.serviceWorker.removeEventListener("controllerchange", changed); document.removeEventListener("visibilitychange", refresh); };
  }, []);
  function activate() { if (waiting) { accepted.current = true; waiting.postMessage({ type: "ACCEPT_UPDATE" }); } }
  return { waiting, failed, activate };
}
