"use client";

import { useEffect, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { readSession } from "@/api/catalog";

export function AccountSnapshot({ identity, children }: { identity: number | null; children: ReactNode }) {
  const client = useQueryClient();
  const session = useQuery({ queryKey: ["private", "session"], queryFn: ({ signal }) => readSession(signal) });
  const changed = session.data !== undefined && (session.data.user?.id ?? null) !== identity;
  useEffect(() => {
    if (changed) { client.clear(); window.location.reload(); }
  }, [changed, client]);
  return changed ? null : children;
}
