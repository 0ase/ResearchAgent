"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { retryResearchTask } from "@/lib/api/client";
import { taskQueryKeys } from "@/features/tasks/task-queries";

export function useRetryTask(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const task = await retryResearchTask(taskId);
      if (!task) throw new Error("重试任务没有返回结果");
      return task;
    },
    onSuccess: (task) => {
      void queryClient.invalidateQueries({ queryKey: taskQueryKeys.all });
      return task;
    },
  });
}
