"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { useTask } from "@/features/tasks/hooks/use-task";
import {
  replayStateToSnapshot,
  snapshotToReplayState,
} from "@/features/tasks/task-cache";
import { taskQueryKeys } from "@/features/tasks/task-queries";
import { getApiBaseUrl, type TaskSnapshotResponse } from "@/lib/api/client";
import { allEventTypes } from "@/lib/events/schemas";
import { reduceResearchEvent } from "@/lib/events/reducer";
import type { ReplayState } from "@/lib/events/types";
import { usePetRuntimeStore } from "@/features/pet/pet-runtime-store";

export type TaskConnectionStatus =
  "idle" | "connecting" | "connected" | "reconnecting" | "closed";

export function useTaskEvents(taskId: string) {
  const queryClient = useQueryClient();
  const taskQuery = useTask(taskId);
  // The snapshot identity is the connection boundary; event-driven cache updates must not reconnect SSE.
  const initialReplayState = useMemo(
    () => (taskQuery.data ? snapshotToReplayState(taskQuery.data) : null),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [taskQuery.data?.id],
  );
  const [eventState, setEventState] = useState<ReplayState | null>(null);
  const [connectionStatus, setConnectionStatus] =
    useState<TaskConnectionStatus>("idle");
  const stateRef = useRef<ReplayState | null>(null);

  useEffect(() => {
    if (!initialReplayState) return;

    const initialState = initialReplayState;
    stateRef.current = initialState;
    usePetRuntimeStore.getState().syncReplayState(initialState);

    if (typeof EventSource === "undefined") {
      queueMicrotask(() => setConnectionStatus("closed"));
      return;
    }

    queueMicrotask(() => setConnectionStatus("connecting"));
    const source = new EventSource(
      `${getApiBaseUrl()}/api/v1/research/tasks/${encodeURIComponent(taskId)}/events?after=${initialState.lastSequence}`,
    );
    queueMicrotask(() => setConnectionStatus("connected"));

    const onEvent = (message: MessageEvent<string>) => {
      let value: unknown;
      try {
        value = JSON.parse(message.data);
      } catch {
        return;
      }

      const result = reduceResearchEvent(
        stateRef.current ?? initialState,
        value,
      );
      if (result.status !== "applied") return;

      stateRef.current = result.state;
      setEventState(result.state);
      queryClient.setQueryData<TaskSnapshotResponse>(
        taskQueryKeys.detail(taskId),
        (existing) =>
          existing ? replayStateToSnapshot(existing, result.state) : existing,
      );
      queryClient.setQueryData<TaskSnapshotResponse | null>(
        taskQueryKeys.active(),
        (existing) =>
          existing?.id === taskId
            ? replayStateToSnapshot(existing, result.state)
            : existing,
      );
      usePetRuntimeStore.getState().syncReplayState(result.state);
      if (result.state.isTerminal) {
        source.close();
        setConnectionStatus("closed");
      }
    };

    for (const eventType of allEventTypes) {
      source.addEventListener(eventType, onEvent);
    }
    source.onerror = () => setConnectionStatus("reconnecting");

    return () => {
      for (const eventType of allEventTypes) {
        source.removeEventListener(eventType, onEvent);
      }
      source.close();
      setConnectionStatus("closed");
    };
  }, [initialReplayState, queryClient, taskId]);

  return {
    task: taskQuery.data,
    replayState: eventState ?? initialReplayState,
    connectionStatus,
    isLoading: taskQuery.isPending,
    error: taskQuery.error,
  };
}
