import type { EventType, ResearchEvent } from "@/lib/events/types";

const taskId = "fixture-task";

function makeEvent(
  eventType: EventType,
  sequence: number,
  payload: Record<string, unknown> = {},
  stage?: ResearchEvent["stage"],
): ResearchEvent {
  return {
    schema_version: 1,
    task_id: taskId,
    sequence,
    event_type: eventType,
    stage,
    level: "info",
    payload,
    occurred_at: `2026-08-19T10:01:${String(sequence).padStart(2, "0")}Z`,
  };
}

export const successEvents: ResearchEvent[] = [
  makeEvent("task.created", 1),
  makeEvent("task.started", 2),
  makeEvent("stage.started", 3, { attempt: 1 }, "search"),
  makeEvent("papers.discovered", 4, { count: 8 }, "search"),
  makeEvent("stage.progress", 5, { message: "Found 8 papers" }, "search"),
  makeEvent("stage.completed", 6, { duration_ms: 640 }, "search"),
  makeEvent("result.available", 7, { report_markdown: "# Result" }),
  makeEvent("task.completed", 8),
];

export const partialSuccessEvents: ResearchEvent[] = [
  makeEvent("task.created", 1),
  makeEvent("task.started", 2),
  makeEvent("stage.warning", 3, { message: "PubMed timed out" }, "search"),
  makeEvent("papers.discovered", 4, { count: 3 }, "search"),
  makeEvent("result.available", 5, { partial: true }),
  makeEvent("task.completed", 6, { warnings: ["One source was unavailable"] }),
];

export const criticRevisionEvents: ResearchEvent[] = [
  makeEvent("stage.started", 1, { attempt: 1 }, "critic"),
  makeEvent(
    "critique.completed",
    2,
    { attempt: 1, summary: "Add sources" },
    "critic",
  ),
  makeEvent("stage.started", 3, { attempt: 2 }, "critic"),
  makeEvent(
    "critique.completed",
    4,
    { attempt: 2, summary: "Ready" },
    "critic",
  ),
];

export const failureEvents: ResearchEvent[] = [
  makeEvent("task.created", 1),
  makeEvent("task.started", 2),
  makeEvent(
    "stage.failed",
    3,
    { code: "SEARCH_FAILED", message: "Search unavailable" },
    "search",
  ),
  makeEvent("task.failed", 4, {
    code: "SEARCH_FAILED",
    message: "Search unavailable",
  }),
];
