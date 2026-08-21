"use client";

import { useQuery } from "@tanstack/react-query";

import { getResearchTask, type TaskSnapshotResponse } from "@/lib/api/client";
import { taskQueryKeys } from "@/features/tasks/task-queries";

export function useTask(
  taskId: string,
  { enabled = Boolean(taskId) }: { enabled?: boolean } = {},
) {
  return useQuery<TaskSnapshotResponse, Error>({
    queryKey: taskQueryKeys.detail(taskId),
    queryFn: async () => {
      const task = await getResearchTask(taskId);
      if (!task) throw new Error("任务快照为空");
      return task;
    },
    enabled,
    retry: false,
  });
}
