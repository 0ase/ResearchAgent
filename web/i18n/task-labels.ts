import type {
  ResearchStage,
  StageStatus,
  TaskStatus,
} from "@/lib/events/types";

export const taskStageMessageKeys = {
  orchestrate: "stage.orchestrate",
  search: "stage.search",
  filter: "stage.filter",
  read: "stage.read",
  analyze: "stage.analyze",
  synthesize: "stage.synthesize",
  critic: "stage.critic",
} as const satisfies Record<ResearchStage, string>;

export const taskStageStatusMessageKeys = {
  pending: "stageStatus.pending",
  running: "stageStatus.running",
  completed: "stageStatus.completed",
  warning: "stageStatus.warning",
  failed: "stageStatus.failed",
  cancelled: "stageStatus.cancelled",
} as const satisfies Record<StageStatus, string>;

export const taskStatusMessageKeys = {
  queued: "status.queued",
  running: "status.running",
  cancelling: "status.cancelling",
  completed: "status.completed",
  failed: "status.failed",
  cancelled: "status.cancelled",
  interrupted: "status.interrupted",
} as const satisfies Record<TaskStatus, string>;
