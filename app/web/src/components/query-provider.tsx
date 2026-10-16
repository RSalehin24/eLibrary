"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { UpdateSafetyProvider } from "@/lib/update-safety";
import { AccountBoundary } from "./account-boundary";

export function QueryProvider({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient({
    defaultOptions: {
      queries: { staleTime: 30_000, gcTime: 300_000, retry: 1, refetchOnWindowFocus: true },
      mutations: { retry: false },
    },
  }));
  return <QueryClientProvider client={client}><AccountBoundary /><UpdateSafetyProvider>{children}</UpdateSafetyProvider></QueryClientProvider>;
}
