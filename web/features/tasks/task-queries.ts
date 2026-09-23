export const taskQueryKeys = {
  all: ["research"] as const,
  active: () => [...taskQueryKeys.all, "active"] as const,
  detail: (taskId: string) => [...taskQueryKeys.all, "task", taskId] as const,
};
