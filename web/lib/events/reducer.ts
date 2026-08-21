import { parseResearchEvent } from "@/lib/events/schemas";
import {
  RESEARCH_STAGES,
  type EventPayload,
  type ResearchEvent,
  type ResearchStage,
  type ReplayState,
  type ReduceResult,
  type StageSnapshot,
  type TaskStatus,
} from "@/lib/events/types";

const terminalStatuses = new Set<TaskStatus>([
  "completed",
  "failed",
  "cancelled",
  "interrupted",
]);

export function createInitialReplayState(taskId: string): ReplayState {
  const stages = {} as Record<ResearchStage, StageSnapshot>;
  for (const stage of RESEARCH_STAGES) {
    stages[stage] = {
      status: "pending",
      startedAt: null,
      completedAt: null,
      durationMs: null,
      detail: null,
      attempt: 1,
    };
  }

  return {
    taskId,
    lastSequence: 0,
    taskStatus: "queued",
    currentStage: null,
    stages,
    metrics: {},
    artifacts: {
      planAvailable: false,
      papersDiscovered: false,
      papersSelected: false,
      analysisAvailable: false,
      reportAvailable: false,
      critiqueAvailable: false,
      evidenceAvailable: false,
      resultAvailable: false,
    },
    warnings: [],
    errors: [],
    critic: { attempt: 1, summary: null },
    isTerminal: false,
  };
}

export function reduceResearchEvent(
  state: ReplayState,
  input: unknown,
): ReduceResult {
  const parsed = parseResearchEvent(input);
  if (parsed.status === "unknown") {
    return { status: "ignored", state, reason: "unknown_event" };
  }
  if (parsed.status === "rejected") {
    return { status: "rejected", state, reason: "invalid_event" };
  }

  const event = parsed.event;
  if (event.task_id !== state.taskId) {
    return { status: "rejected", state, reason: "task_mismatch" };
  }
  if (event.sequence < state.lastSequence) {
    return { status: "ignored", state, reason: "out_of_order" };
  }
  if (event.sequence === state.lastSequence) {
    return { status: "ignored", state, reason: "duplicate_sequence" };
  }

  const next = applyEvent(state, event);
  next.lastSequence = event.sequence;
  return { status: "applied", state: next, event };
}

export function replayEvents(
  taskId: string,
  events: readonly unknown[],
): ReplayState {
  return events.reduce<ReplayState>(
    (state, event) => reduceResearchEvent(state, event).state,
    createInitialReplayState(taskId),
  );
}

function applyEvent(state: ReplayState, event: ResearchEvent): ReplayState {
  const next: ReplayState = {
    ...state,
    stages: { ...state.stages },
    metrics: { ...state.metrics },
    artifacts: { ...state.artifacts },
    warnings: [...state.warnings],
    errors: [...state.errors],
    critic: { ...state.critic },
  };

  switch (event.event_type) {
    case "task.created":
      next.taskStatus = "queued";
      break;
    case "task.started":
      next.taskStatus = "running";
      break;
    case "task.cancellation_requested":
      next.taskStatus = "cancelling";
      break;
    case "task.cancelled":
      next.taskStatus = "cancelled";
      break;
    case "task.completed":
      next.taskStatus = "completed";
      appendWarnings(next, event.payload);
      break;
    case "task.failed":
      next.taskStatus = "failed";
      appendError(next, event.payload);
      break;
    case "task.interrupted":
      next.taskStatus = "interrupted";
      appendError(next, event.payload);
      break;
    case "stage.started":
      updateStage(next, event, "running");
      break;
    case "stage.progress":
      updateStage(next, event, "running");
      mergeMetrics(next, event.payload);
      break;
    case "stage.warning":
      updateStage(next, event, "warning");
      appendWarnings(next, event.payload);
      break;
    case "stage.completed":
      updateStage(next, event, "completed");
      break;
    case "stage.failed":
      updateStage(next, event, "failed");
      appendError(next, event.payload);
      break;
    case "plan.available":
      next.artifacts.planAvailable = true;
      break;
    case "papers.discovered":
      next.artifacts.papersDiscovered = true;
      setCount(next, "papersDiscovered", event.payload.count);
      break;
    case "papers.selected":
      next.artifacts.papersSelected = true;
      setCount(next, "papersSelected", event.payload.count);
      break;
    case "paper.read":
      next.metrics.papersRead = (next.metrics.papersRead ?? 0) + 1;
      break;
    case "analysis.available":
      next.artifacts.analysisAvailable = true;
      break;
    case "draft.available":
      next.artifacts.reportAvailable = true;
      break;
    case "critique.completed":
      next.artifacts.critiqueAvailable = true;
      next.critic.attempt = Math.max(
        next.critic.attempt,
        numberValue(event.payload.attempt) ?? next.critic.attempt,
      );
      next.critic.summary =
        stringValue(event.payload.summary) ?? next.critic.summary;
      break;
    case "evidence.available":
      next.artifacts.evidenceAvailable = true;
      break;
    case "result.available":
      next.artifacts.resultAvailable = true;
      break;
  }

  next.isTerminal = terminalStatuses.has(next.taskStatus);
  return next;
}

function updateStage(
  state: ReplayState,
  event: ResearchEvent,
  status: StageSnapshot["status"],
): void {
  if (!event.stage) return;
  const current = state.stages[event.stage];
  const attempt = numberValue(event.payload.attempt) ?? current.attempt;
  state.currentStage = event.stage;
  state.stages[event.stage] = {
    ...current,
    status,
    attempt,
    startedAt:
      status === "running" && !current.startedAt
        ? event.occurred_at
        : current.startedAt,
    completedAt:
      status === "completed" || status === "failed"
        ? event.occurred_at
        : current.completedAt,
    durationMs: numberValue(event.payload.duration_ms) ?? current.durationMs,
    detail:
      stringValue(event.payload.detail) ??
      stringValue(event.payload.message) ??
      current.detail,
  };
  state.critic.attempt = Math.max(state.critic.attempt, attempt);
}

function mergeMetrics(state: ReplayState, payload: EventPayload): void {
  const metrics = payload.metrics;
  if (!metrics || typeof metrics !== "object" || Array.isArray(metrics)) return;
  for (const [key, value] of Object.entries(metrics)) {
    if (typeof value === "number" && Number.isFinite(value)) {
      state.metrics[key] = value;
    }
  }
}

function setCount(state: ReplayState, key: string, value: unknown): void {
  const count = numberValue(value);
  if (count !== null) state.metrics[key] = count;
}

function appendWarnings(state: ReplayState, payload: EventPayload): void {
  const warnings = Array.isArray(payload.warnings)
    ? payload.warnings.filter(
        (value): value is string => typeof value === "string",
      )
    : [];
  const message = stringValue(payload.message);
  for (const warning of [...warnings, ...(message ? [message] : [])]) {
    if (!state.warnings.includes(warning)) state.warnings.push(warning);
  }
}

function appendError(state: ReplayState, payload: EventPayload): void {
  const message =
    stringValue(payload.message) ?? stringValue(payload.code) ?? "研究任务失败";
  if (!state.errors.includes(message)) state.errors.push(message);
}

function numberValue(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" && value.length > 0 ? value : null;
}
