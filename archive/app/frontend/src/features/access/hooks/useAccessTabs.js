import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { normalizeAccessTab } from "../constants";

export function useAccessTabs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [activeTab, setActiveTab] = useState(() =>
    normalizeAccessTab(searchParams.get("tab")),
  );

  function applyActiveTab(nextTab, options = {}) {
    const { replace = false } = options;
    const normalizedTab = normalizeAccessTab(nextTab);
    setActiveTab(normalizedTab);

    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("tab", normalizedTab);
    setSearchParams(nextParams, { replace });
  }

  useEffect(() => {
    const normalizedTab = normalizeAccessTab(searchParams.get("tab"));
    if (activeTab !== normalizedTab) {
      setActiveTab(normalizedTab);
      return;
    }

    if (searchParams.get("tab") !== normalizedTab) {
      const nextParams = new URLSearchParams(searchParams);
      nextParams.set("tab", normalizedTab);
      setSearchParams(nextParams, { replace: true });
    }
  }, [activeTab, searchParams, setSearchParams]);

  return {
    activeTab,
    applyActiveTab,
  };
}
