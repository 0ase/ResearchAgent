import {
  deleteResearchTask,
  getResearchHistory,
  updateResearchTask,
} from "@/lib/api/client";

export const historyQueryKeys = {
  all: ["research-history"] as const,
  list: (limit: number) => ["research-history", { limit }] as const,
};

export { deleteResearchTask, getResearchHistory, updateResearchTask };
