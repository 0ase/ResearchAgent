"use client";

import { useQuery } from "@tanstack/react-query";

import { getResearchTask, type TaskSnapshotResponse } from "@/lib/api/client";
import { taskQueryKeys } from "@/features/tasks/task-queries";
import { mergeTaskSnapshot } from "@/features/tasks/task-cache";

export function useTask(
  taskId: string,
  { enabled = Boolean(taskId), pollCancellation = false }: { enabled?: boolean; pollCancellation?: boolean } = {},
) {
  return useQuery<TaskSnapshotResponse, Error>({
    queryKey: taskQueryKeys.detail(taskId),
    queryFn: async () => {
      const task = await getResearchTask(taskId);
      if (!task) throw new Error("任务快照为空");
      return task;
    },
    enabled,
    refetchInterval: (query) => pollCancellation && query.state.data?.status === "cancelling" ? 1_000 : false,
    refetchIntervalInBackground: pollCancellation,
    structuralSharing: (existing, incoming) => mergeTaskSnapshot(
      existing as TaskSnapshotResponse | undefined,
      incoming as TaskSnapshotResponse,
    ),
    retry: false,
  });
}
