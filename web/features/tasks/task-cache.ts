import type { TaskSnapshotResponse } from "@/lib/api/client";
import { replaceEqualDeep } from "@tanstack/react-query";
import { replayEvents } from "@/lib/events/reducer";
import {
  RESEARCH_STAGES,
  type ReplayState,
  type ResearchStage,
  type StageStatus,
  type ResearchEvent,
} from "@/lib/events/types";

export function mergeTaskSnapshot(
  existing: TaskSnapshotResponse | undefined,
  incoming: TaskSnapshotResponse,
): TaskSnapshotResponse {
  if (existing?.id === incoming.id) {
    const terminal = ["completed", "failed", "cancelled", "interrupted"];
    if (
      incoming.last_sequence < existing.last_sequence ||
      (terminal.includes(existing.status) && !terminal.includes(incoming.status)) ||
      (existing.status === "cancelling" && ["queued", "running"].includes(incoming.status))
    ) return existing;
  }
  return replaceEqualDeep(existing, incoming);
}

export function snapshotToReplayState(
  snapshot: TaskSnapshotResponse,
): ReplayState {
  const state = replayEvents(snapshot.id, snapshot.replay_events ?? []);
  state.lastSequence = snapshot.last_sequence;
  state.taskStatus = snapshot.status;
  state.currentStage = snapshot.current_stage ?? null;
  state.isTerminal = [
    "completed",
    "failed",
    "cancelled",
    "interrupted",
  ].includes(snapshot.status);
  for (const [key, value] of Object.entries(snapshot.statistics ?? {})) {
    if (typeof value === "number" && Number.isFinite(value))
      state.metrics[key] = value;
  }
  for (const stage of snapshot.stages ?? []) {
    const stageName = stage.stage as ResearchStage;
    if (!RESEARCH_STAGES.includes(stageName)) continue;
    state.stages[stageName] = {
      status: stage.status as StageStatus,
      startedAt: stage.started_at ?? null,
      completedAt: stage.completed_at ?? null,
      durationMs: stage.duration_ms ?? null,
      detail: stage.detail ?? null,
      attempt: stage.attempt ?? 1,
    };
  }
  if (snapshot.status === "cancelled") {
    for (const stage of RESEARCH_STAGES) {
      if (state.stages[stage].status === "running") state.stages[stage].status = "cancelled";
    }
  }
  return state;
}

export function replayStateToSnapshot(
  snapshot: TaskSnapshotResponse,
  state: ReplayState,
  event?: ResearchEvent,
): TaskSnapshotResponse {
  return {
    ...snapshot,
    replay_events:
      event &&
      !(snapshot.replay_events ?? []).some(
        (item) => item.sequence === event.sequence,
      )
        ? [...(snapshot.replay_events ?? []), event]
        : snapshot.replay_events,
    status: state.taskStatus,
    available_actions: state.isTerminal
      ? ["retry", "rename", "delete"]
      : state.taskStatus === "cancelling" ? [] : ["cancel"],
    current_stage: state.currentStage,
    last_sequence: Math.max(snapshot.last_sequence, state.lastSequence),
    statistics: { ...snapshot.statistics, ...state.metrics },
    stages: RESEARCH_STAGES.map((stage) => {
      const current = state.stages[stage];
      return {
        stage,
        status: current.status,
        started_at: current.startedAt,
        completed_at: current.completedAt,
        duration_ms: current.durationMs,
        detail: current.detail,
        attempt: current.attempt,
      };
    }),
  };
}
