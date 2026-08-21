"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  getDeepSeekSettings,
  updateDeepSeekSettings,
  type DeepSeekSettingsResponse,
  type UpdateDeepSeekSettingsRequest,
} from "@/lib/api/client";

export const deepSeekSettingsQueryKey = ["settings", "deepseek"] as const;

export function useDeepSeekSettings() {
  return useQuery({
    queryKey: deepSeekSettingsQueryKey,
    queryFn: async () => {
      const response = await getDeepSeekSettings();
      if (!response) throw new Error("DeepSeek settings response was empty");
      return response;
    },
    staleTime: 30_000,
    retry: false,
  });
}

export function useUpdateDeepSeekSettings() {
  const queryClient = useQueryClient();
  return useMutation<
    DeepSeekSettingsResponse,
    Error,
    UpdateDeepSeekSettingsRequest
  >({
    mutationFn: async (request) => {
      const response = await updateDeepSeekSettings(request);
      if (!response) throw new Error("DeepSeek settings response was empty");
      return response;
    },
    onSuccess: (response) => {
      queryClient.setQueryData(deepSeekSettingsQueryKey, response);
    },
  });
}
