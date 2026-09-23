"use client";

import { useQuery } from "@tanstack/react-query";

import {
  getResearchResult,
  type ResearchTaskResultResponse,
} from "@/lib/api/client";

export function useTaskResult(taskId: string, enabled = true) {
  return useQuery<ResearchTaskResultResponse, Error>({
    queryKey: ["research", "task", taskId, "result"],
    queryFn: async () => {
      const result = await getResearchResult(taskId);
      if (!result) throw new Error("研究结果为空");
      return result;
    },
    enabled: Boolean(taskId) && enabled,
    retry: false,
  });
}
