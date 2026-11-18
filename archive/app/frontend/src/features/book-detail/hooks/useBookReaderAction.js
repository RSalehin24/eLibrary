import { useState } from "react";
import { bookDetailFetch, resolveBookDetailUrl } from "../api";
import { launchBookReader } from "../readerLaunch";
import { waitForMinimumLoader, waitForUiFrame } from "../utils";

export function useBookReaderAction({ navigate, slug, toast }) {
  const [launchingReader, setLaunchingReader] = useState(false);

  async function launchReader() {
    if (launchingReader) {
      return;
    }

    try {
      setLaunchingReader(true);
      const startedAt = Date.now();
      await waitForUiFrame();
      await launchBookReader({
        slug,
        apiClient: bookDetailFetch,
        navigate,
        resolveUrl: resolveBookDetailUrl
      });
      await waitForMinimumLoader(startedAt);
    } catch (nextError) {
      toast.error(nextError.message);
    } finally {
      setLaunchingReader(false);
    }
  }

  return {
    launchReader,
    launchingReader
  };
}
