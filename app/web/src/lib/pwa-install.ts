import { useEffect, useState, useSyncExternalStore } from "react";

type InstallEvent = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: "accepted" | "dismissed" }> };

function isInstalled() { return window.matchMedia("(display-mode: standalone)").matches; }
function subscribeInstalled(listener: () => void) {
  const media = window.matchMedia("(display-mode: standalone)");
  media.addEventListener("change", listener);
  window.addEventListener("appinstalled", listener);
  return () => { media.removeEventListener("change", listener); window.removeEventListener("appinstalled", listener); };
}

export function useInstallPrompt() {
  const [prompt, setPrompt] = useState<InstallEvent | null>(null);
  const [failed, setFailed] = useState(false);
  const [accepted, setAccepted] = useState(false);
  const installed = useSyncExternalStore(subscribeInstalled, isInstalled, () => false);
  useEffect(() => {
    const capture = (event: Event) => {
      event.preventDefault();
      try { if (!localStorage.getItem("library-install-dismissed")) setPrompt(event as InstallEvent); }
      catch { setFailed(true); setPrompt(null); }
    };
    window.addEventListener("beforeinstallprompt", capture);
    return () => window.removeEventListener("beforeinstallprompt", capture);
  }, []);
  async function install() {
    if (!prompt) return;
    try { await prompt.prompt(); const choice = await prompt.userChoice; if (choice.outcome === "dismissed") localStorage.setItem("library-install-dismissed", "1"); else setAccepted(true); setPrompt(null); }
    catch { setFailed(true); setPrompt(null); }
  }
  return { available: !!prompt && !installed && !accepted, installed, failed, install };
}
