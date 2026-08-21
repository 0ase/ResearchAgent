"use client";

import { useMutation } from "@tanstack/react-query";

import {
  ApiNetworkError,
  createResearchTask,
  type CreateTaskRequest,
  type CreateTaskResponse,
} from "@/lib/api/client";

export function useCreateTask() {
  return useMutation<CreateTaskResponse, Error, CreateTaskRequest>({
    mutationFn: async (request) => {
      const response = await createResearchTask(request);
      if (!response) throw new Error("创建任务没有返回结果");
      return response;
    },
    retry: (failureCount, error) =>
      failureCount < 1 && error instanceof ApiNetworkError,
  });
}
