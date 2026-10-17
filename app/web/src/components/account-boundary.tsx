"use client";

import { useCallback, useEffect, useRef } from "react";
import { useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";
import type { WorkspaceSession } from "@/api/types";
import { subscribeAccountChanges } from "@/lib/account-channel";

function useAccountIdentity(client: QueryClient, session?: WorkspaceSession) {
  const previousIdentity = useRef<number | null | undefined>(undefined);
  useEffect(() => {
    if (!session) return;
    const identity = session.user?.id ?? null;
    if (previousIdentity.current !== undefined && previousIdentity.current !== identity) {
      client.clear(); window.location.reload();
    }
    previousIdentity.current = identity;
  }, [client, session]);
  return useCallback(() => { previousIdentity.current = undefined; }, []);
}

function useAccountEvents(client: QueryClient, resetIdentity: () => void) {
  useEffect(() => subscribeAccountChanges(() => {
    client.clear(); window.location.reload();
  }, resetIdentity), [client, resetIdentity]);
  useEffect(() => {
    const checkSession = async () => {
      if (document.visibilityState !== "visible") return;
      await client.cancelQueries({ queryKey: ["private", "session"] });
      await client.invalidateQueries({ queryKey: ["private", "session"] });
    };
    window.addEventListener("focus", checkSession); window.addEventListener("pageshow", checkSession);
    return () => { window.removeEventListener("focus", checkSession); window.removeEventListener("pageshow", checkSession); };
  }, [client]);
}

export function AccountBoundary() {
  const client = useQueryClient();
  const session = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal), refetchOnMount: "always", refetchOnWindowFocus: "always" });
  const resetIdentity = useAccountIdentity(client, session.data);
  useAccountEvents(client, resetIdentity);
  return null;
}
