"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";

import { cancelResearchTask } from "@/lib/api/client";
import { taskQueryKeys } from "@/features/tasks/task-queries";

export function useCancelTask(taskId: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const task = await cancelResearchTask(taskId);
      if (!task) throw new Error("取消任务没有返回结果");
      return task;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({
        queryKey: taskQueryKeys.detail(taskId),
      });
      void queryClient.invalidateQueries({ queryKey: taskQueryKeys.active() });
    },
  });
}
