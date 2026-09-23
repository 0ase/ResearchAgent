"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { z } from "zod";
import { apiRequest } from "@/lib/api/client";

const conversationSchema = z.object({
  task_id: z.string(),
  task_status: z.string(),
  messages: z.array(
    z.object({
      message_id: z.string(),
      role: z.enum(["user", "assistant"]),
      content: z.string(),
      citations: z.array(z.string()),
      created_at: z.string(),
    }),
  ),
  pending: z
    .object({
      message_id: z.string(),
      content: z.string(),
      status: z.enum(["queued", "processing", "failed"]),
      error_code: z.string().nullable().optional(),
      created_at: z.string(),
    })
    .nullable(),
});
export type Conversation = z.infer<typeof conversationSchema>;

export function useConversation(taskId: string, taskStatus?: string) {
  const client = useQueryClient();
  const key = ["research", "task", taskId, "messages", taskStatus];
  const path = `/api/v1/research/tasks/${encodeURIComponent(taskId)}`;
  const query = useQuery({
    queryKey: key,
    queryFn: async () =>
      (await apiRequest(
        `${path}/messages`,
        undefined,
        conversationSchema.parse,
      ))!,
    enabled: Boolean(taskStatus),
    retry: false,
    refetchInterval: (query) =>
      ["queued", "processing"].includes(query.state.data?.pending?.status ?? "")
        ? 700
        : false,
  });
  const submit = useMutation({
    mutationFn: async (body: { message_id: string; message: string }) =>
      (await apiRequest(
        `${path}/follow-up`,
        { method: "PUT", body: JSON.stringify(body) },
        conversationSchema.parse,
      ))!,
    onSuccess: (data) =>
      client.setQueriesData(
        { queryKey: ["research", "task", taskId, "messages"] },
        data,
      ),
  });
  const cancel = useMutation({
    mutationFn: () => apiRequest(`${path}/follow-up`, { method: "DELETE" }),
    onSuccess: () =>
      client.invalidateQueries({
        queryKey: ["research", "task", taskId, "messages"],
      }),
  });
  return { query, submit, cancel };
}
