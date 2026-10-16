export async function configureInstallationSimulator(page) {
  await page.addInitScript(() => {
    const nativeMatchMedia = window.matchMedia.bind(window);
    const standalone = new EventTarget();
    Object.defineProperties(standalone, {
      matches: { get: () => localStorage.getItem("simulator-app-installed") === "1" },
      media: { value: "(display-mode: standalone)" },
    });
    window.matchMedia = (query) => query === standalone.media ? standalone : nativeMatchMedia(query);
    window.simulateAppMode = (installed) => {
      localStorage.setItem("simulator-app-installed", installed ? "1" : "0");
      standalone.dispatchEvent(new Event("change"));
      if (installed) window.dispatchEvent(new Event("appinstalled"));
    };
  });
}

export async function offerInstallation(page, outcome) {
  await page.evaluate((choice) => {
    window.installPromptCount = 0;
    const event = new Event("beforeinstallprompt", { cancelable: true });
    event.prompt = async () => { window.installPromptCount += 1; };
    event.userChoice = Promise.resolve({ outcome: choice });
    window.dispatchEvent(event);
  }, outcome);
}
