export const EVENT_TYPES = [
  "task.created",
  "task.started",
  "task.cancellation_requested",
  "task.cancelled",
  "task.completed",
  "task.failed",
  "task.interrupted",
  "stage.started",
  "stage.progress",
  "stage.warning",
  "stage.completed",
  "stage.failed",
  "plan.available",
  "papers.discovered",
  "papers.selected",
  "paper.read",
  "analysis.available",
  "draft.available",
  "critique.completed",
  "evidence.available",
  "result.available",
] as const;

export type EventType = (typeof EVENT_TYPES)[number];

export const RESEARCH_STAGES = [
  "orchestrate",
  "search",
  "filter",
  "read",
  "analyze",
  "synthesize",
  "critic",
] as const;

export type ResearchStage = (typeof RESEARCH_STAGES)[number];

export type EventLevel = "info" | "warning" | "error";
export type TaskStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "completed"
  | "failed"
  | "cancelled"
  | "interrupted";
export type StageStatus =
  "pending" | "running" | "completed" | "warning" | "failed" | "cancelled";

export type EventPayload = Record<string, unknown>;

export type ResearchEvent = {
  schema_version: number;
  task_id: string;
  sequence: number;
  event_type: EventType;
  stage?: ResearchStage | null;
  level: EventLevel;
  payload: EventPayload;
  occurred_at: string;
};

export type StageSnapshot = {
  status: StageStatus;
  startedAt: string | null;
  completedAt: string | null;
  durationMs: number | null;
  detail: string | null;
  attempt: number;
};

export type ReplayArtifacts = {
  planAvailable: boolean;
  papersDiscovered: boolean;
  papersSelected: boolean;
  analysisAvailable: boolean;
  reportAvailable: boolean;
  critiqueAvailable: boolean;
  evidenceAvailable: boolean;
  resultAvailable: boolean;
};

export type ReplayState = {
  taskId: string;
  lastSequence: number;
  taskStatus: TaskStatus;
  currentStage: ResearchStage | null;
  stages: Record<ResearchStage, StageSnapshot>;
  metrics: Record<string, number>;
  artifacts: ReplayArtifacts;
  warnings: string[];
  errors: string[];
  critic: {
    attempt: number;
    summary: string | null;
  };
  isTerminal: boolean;
};

export type ParseResearchEventResult =
  | { status: "accepted"; event: ResearchEvent }
  | { status: "unknown"; event: unknown; reason: "unknown_event" }
  | { status: "rejected"; event: unknown; reason: "invalid_event" };

export type ReduceResult =
  | { status: "applied"; state: ReplayState; event: ResearchEvent }
  | {
      status: "ignored";
      state: ReplayState;
      reason: "unknown_event" | "duplicate_sequence" | "out_of_order";
    }
  | {
      status: "rejected";
      state: ReplayState;
      reason: "invalid_event" | "task_mismatch";
    };
