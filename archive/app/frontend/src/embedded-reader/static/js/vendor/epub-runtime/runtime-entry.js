import { initializeEpubRuntime } from "./module-loader.js";
import { coreUtilityModules } from "./modules/core-utilities.modules.js";
import { renderingEngineModules } from "./modules/rendering-engine.modules.js";
import { contentParserModules } from "./modules/content-parsers.modules.js";
import { navigationEngineModules } from "./modules/navigation-engine.modules.js";
import { archiveLoadingModules } from "./modules/archive-loading.modules.js";
import { compatibilityShimModules } from "./modules/compatibility-shims.modules.js";
import { binaryHelperModules } from "./modules/binary-helpers.modules.js";
import { asyncSchedulingModules } from "./modules/async-scheduling.modules.js";

const EPUB_RUNTIME_MODULES = {
  ...coreUtilityModules,
  ...renderingEngineModules,
  ...contentParserModules,
  ...navigationEngineModules,
  ...archiveLoadingModules,
  ...compatibilityShimModules,
  ...binaryHelperModules,
  ...asyncSchedulingModules
};

let runtimeInitializationPromise = null;

export function ensureEpubRuntime() {
  if (typeof window === "undefined") {
    return Promise.resolve(null);
  }

  if (typeof window.ePub === "function") {
    return Promise.resolve(window.ePub);
  }

  if (!runtimeInitializationPromise) {
    runtimeInitializationPromise = Promise.resolve(
      initializeEpubRuntime(EPUB_RUNTIME_MODULES)
    )
      .then((epubApi) => {
        const resolvedApi = typeof window.ePub === "function" ? window.ePub : epubApi;
        if (typeof resolvedApi !== "function") {
          throw new Error("EPUB runtime did not expose a callable ePub API.");
        }

        runtimeInitializationPromise = Promise.resolve(resolvedApi);
        return resolvedApi;
      })
      .catch((error) => {
        runtimeInitializationPromise = null;
        throw error;
      });
  }

  return runtimeInitializationPromise;
}

if (typeof window !== "undefined") {
  window.__epubRuntimeReady = ensureEpubRuntime();
}
