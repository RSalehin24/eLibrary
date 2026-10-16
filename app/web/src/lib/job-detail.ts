"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { controlJob, readJob } from "@/api/jobs";
import type { BackgroundJobDetail, JobControl } from "@/api/types";
import { jobPollingInterval } from "./job-status";
import { useUpdateParticipant } from "./update-safety";

export function useJobDetail(initial: BackgroundJobDetail) {
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["private", "jobs", "detail", initial.id], queryFn: ({ signal }) => readJob(initial.id, signal), initialData: initial,
    refetchInterval: (state) => jobPollingInterval(state.state.data ? [state.state.data] : [], state.state.fetchFailureCount), refetchIntervalInBackground: false });
  const command = useMutation({ mutationFn: (action: JobControl["action"]) => controlJob(query.data, action), onSuccess: async () => { await client.invalidateQueries({ queryKey: ["private", "jobs"] }); } });
  useUpdateParticipant({ dirty: command.isPending });
  async function refresh() { const result = await query.refetch(); if (result.isSuccess) command.reset(); }
  return { job: query.data, query, command, refresh };
}
