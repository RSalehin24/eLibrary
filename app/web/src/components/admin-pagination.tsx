"use client";

import type { ManagedAccounts } from "@/api/types";
import { NumberedPagination } from "./numbered-pagination";

export function AdminPagination({ pagination, filter, label }: { pagination: ManagedAccounts["pagination"]; filter: string; label: string }) {
  return <NumberedPagination page={pagination.page} totalPages={Math.max(1, Math.ceil(pagination.total_count / pagination.limit))} query={filter} label={label} />;
}
