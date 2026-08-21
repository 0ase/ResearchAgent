"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { taskQueryKeys } from "@/features/tasks/task-queries";
import {
  deleteResearchTask,
  getResearchHistory,
  historyQueryKeys,
  updateResearchTask,
} from "@/features/history/history-queries";

export function useHistory(limit = 100) {
  return useQuery({
    queryKey: historyQueryKeys.list(limit),
    queryFn: async () => (await getResearchHistory(limit)) ?? [],
  });
}

export function useRenameTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ taskId, title }: { taskId: string; title: string }) =>
      updateResearchTask(taskId, title),
    onSuccess: (_, variables) => {
      void queryClient.invalidateQueries({ queryKey: historyQueryKeys.all });
      void queryClient.invalidateQueries({
        queryKey: taskQueryKeys.detail(variables.taskId),
      });
    },
  });
}

export function useDeleteTask() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (taskId: string) => deleteResearchTask(taskId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: historyQueryKeys.all });
    },
  });
}
