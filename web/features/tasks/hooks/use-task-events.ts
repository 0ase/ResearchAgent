"use client";

import { useQueryClient } from "@tanstack/react-query";
import { createContext, createElement, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from "react";

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
import { historyQueryKeys } from "@/features/history/history-queries";

export type TaskConnectionStatus =
  "idle" | "connecting" | "connected" | "reconnecting" | "closed";

const TaskEventsContext = createContext<ReturnType<typeof useTaskEventConnection> | null>(null);

export function TaskEventsProvider({ taskId, children }: { taskId: string; children: ReactNode }) {
  return createElement(TaskEventsOwner, { key: taskId, taskId }, children);
}

function TaskEventsOwner({ taskId, children }: { taskId: string; children?: ReactNode }) {
  const value = useTaskEventConnection(taskId);
  return createElement(TaskEventsContext.Provider, { value }, children);
}

export function useTaskEvents(taskId: string) {
  const state = useContext(TaskEventsContext);
  if (!state) throw new Error("TaskEventsProvider is required");
  if (state.task && state.task.id !== taskId) throw new Error("Task event scope does not match the task");
  return state;
}

function useTaskEventConnection(taskId: string) {
  const queryClient = useQueryClient();
  const taskQuery = useTask(taskId, { pollCancellation: true });
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
  const sourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!initialReplayState) return;
    let disposed = false;

    const initialState = initialReplayState;
    stateRef.current = initialState;
    usePetRuntimeStore.getState().syncReplayState(initialState);

    if (initialState.isTerminal) {
      queueMicrotask(() => setConnectionStatus("closed"));
      return;
    }

    if (typeof EventSource === "undefined") {
      queueMicrotask(() => setConnectionStatus("closed"));
      return;
    }

    queueMicrotask(() => { if (!disposed) setConnectionStatus("connecting"); });
    const source = new EventSource(
      `${getApiBaseUrl()}/api/v1/research/tasks/${encodeURIComponent(taskId)}/events?after=${initialState.lastSequence}`,
    );
    sourceRef.current = source;
    source.onopen = () => { if (!disposed && !stateRef.current?.isTerminal) setConnectionStatus("connected"); };

    const onEvent = (message: MessageEvent<string>) => {
      if (disposed || stateRef.current?.isTerminal) return;
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
          existing
            ? replayStateToSnapshot(existing, result.state, result.event)
            : existing,
      );
      queryClient.setQueryData<TaskSnapshotResponse | null>(
        taskQueryKeys.active(),
        (existing) =>
          existing?.id === taskId
            ? replayStateToSnapshot(existing, result.state, result.event)
            : existing,
      );
      usePetRuntimeStore.getState().syncReplayState(result.state);
      if (result.state.isTerminal) {
        disposed = true;
        source.close();
        setConnectionStatus("closed");
      }
    };

    for (const eventType of allEventTypes) {
      source.addEventListener(eventType, onEvent);
    }
    source.onerror = () => { if (!disposed && !stateRef.current?.isTerminal) setConnectionStatus("reconnecting"); };

    return () => {
      disposed = true;
      source.onopen = null;
      source.onerror = null;
      for (const eventType of allEventTypes) {
        source.removeEventListener(eventType, onEvent);
      }
      source.close();
      if (sourceRef.current === source) sourceRef.current = null;
    };
  }, [initialReplayState, queryClient, taskId]);

  // REST cancellation and polling snapshots must advance replay without reopening SSE.
  const snapshotReplay = useMemo(
    () => taskQuery.data ? snapshotToReplayState(taskQuery.data) : null,
    [taskQuery.data],
  );
  useEffect(() => {
    if (!snapshotReplay) return;
    if (stateRef.current && snapshotReplay.lastSequence < stateRef.current.lastSequence) return;
    stateRef.current = snapshotReplay;
    usePetRuntimeStore.getState().syncReplayState(snapshotReplay);
    if (snapshotReplay.isTerminal) sourceRef.current?.close();
  }, [snapshotReplay]);

  const terminal = snapshotReplay?.isTerminal ?? false;
  useEffect(() => {
    if (!terminal) return;
    void queryClient.invalidateQueries({ queryKey: taskQueryKeys.active() });
    void queryClient.invalidateQueries({ queryKey: historyQueryKeys.all });
  }, [terminal, queryClient]);

  const replayState = snapshotReplay && (!eventState || snapshotReplay.lastSequence >= eventState.lastSequence)
    ? snapshotReplay : eventState ?? initialReplayState;

  return {
    task: taskQuery.data,
    replayState,
    connectionStatus: replayState?.isTerminal ? "closed" as const : connectionStatus,
    isLoading: taskQuery.isPending,
    error: taskQuery.error,
  };
}
