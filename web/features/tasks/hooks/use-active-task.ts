"use client";

import { useQuery } from "@tanstack/react-query";

import { getActiveTask } from "@/lib/api/client";
import { taskQueryKeys } from "@/features/tasks/task-queries";

export function useActiveTask({ enabled = true }: { enabled?: boolean } = {}) {
  return useQuery({
    queryKey: taskQueryKeys.active(),
    queryFn: async () => (await getActiveTask()) ?? null,
    enabled,
    staleTime: 1_500,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" ||
        status === "running" ||
        status === "cancelling"
        ? 2_000
        : false;
    },
    retry: false,
  });
}
