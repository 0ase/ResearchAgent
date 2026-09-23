"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { cancelResearchTask, type TaskSnapshotResponse } from "@/lib/api/client";
import { taskQueryKeys } from "@/features/tasks/task-queries";
import { mergeTaskSnapshot } from "@/features/tasks/task-cache";
import { historyQueryKeys } from "@/features/history/history-queries";

export function useCancelTask(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const task = await cancelResearchTask(taskId);
      if (!task) throw new Error("取消任务没有返回结果");
      return task;
    },
    onSuccess: (task) => {
      queryClient.setQueryData<TaskSnapshotResponse>(
        taskQueryKeys.detail(taskId),
        (existing) => mergeTaskSnapshot(existing, task),
      );
      void queryClient.invalidateQueries({
        queryKey: taskQueryKeys.detail(taskId),
        exact: true,
      });
      void queryClient.invalidateQueries({ queryKey: taskQueryKeys.active() });
      void queryClient.invalidateQueries({ queryKey: historyQueryKeys.all });
    },
  });
}
