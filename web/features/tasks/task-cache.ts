import type { TaskSnapshotResponse } from "@/lib/api/client";
import { createInitialReplayState } from "@/lib/events/reducer";
import {
  RESEARCH_STAGES,
  type ReplayState,
  type ResearchStage,
  type StageStatus,
} from "@/lib/events/types";

export function snapshotToReplayState(
  snapshot: TaskSnapshotResponse,
): ReplayState {
  const state = createInitialReplayState(snapshot.id);
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
  return state;
}

export function replayStateToSnapshot(
  snapshot: TaskSnapshotResponse,
  state: ReplayState,
): TaskSnapshotResponse {
  return {
    ...snapshot,
    status: state.taskStatus,
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
