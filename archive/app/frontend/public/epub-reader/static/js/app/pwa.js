if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("./service-worker.js", {
        updateViaCache: "none"
      })
      .then((registration) => {
        registration.update().catch(() => {
          // Ignore update checks when browser blocks them.
        });
      })
      .catch(() => {
        // Registration failures should not block core reading functionality.
      });
  });
}

window.addEventListener("load", () => {
  const root = document.documentElement;
  const openEbookPage = document.querySelector(".open-ebook-page");

  if (!root || !openEbookPage) return;

  const syncReaderOpenClass = () => {
    const isHidden = window.getComputedStyle(openEbookPage).display === "none";
    root.classList.toggle("reader-open", isHidden);
  };

  syncReaderOpenClass();

  const observer = new MutationObserver(syncReaderOpenClass);
  observer.observe(openEbookPage, {
    attributes: true,
    attributeFilter: ["style", "class", "hidden"]
  });

  window.addEventListener(
    "pagehide",
    () => {
      observer.disconnect();
    },
    { once: true }
  );
});
