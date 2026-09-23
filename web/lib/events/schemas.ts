import { z } from "zod";

import {
  EVENT_TYPES,
  RESEARCH_STAGES,
  type EventType,
  type ParseResearchEventResult,
  type ResearchEvent,
} from "@/lib/events/types";

const baseEventSchema = z.object({
  schema_version: z.number().int().min(1),
  task_id: z.string().min(1),
  sequence: z.number().int().min(1),
  stage: z.enum(RESEARCH_STAGES).nullable().optional(),
  level: z.enum(["info", "warning", "error"]).default("info"),
  payload: z.record(z.string(), z.unknown()).default({}),
  occurred_at: z.string().datetime({ offset: true }),
});

export const readProgressSchema = z.object({
  attempt: z.number().int().min(1),
  total: z.number().int().nonnegative(),
  completed: z.number().int().nonnegative(),
  succeeded: z.number().int().nonnegative(),
  degraded: z.number().int().nonnegative(),
  failed: z.number().int().nonnegative(),
}).passthrough().refine(p => p.completed <= p.total && p.completed === p.succeeded + p.degraded + p.failed);

function eventSchema<T extends EventType>(eventType: T) {
  return baseEventSchema.extend({ event_type: z.literal(eventType) });
}

export const eventSchemas = {
  "agent.delegated": eventSchema("agent.delegated").extend({
    payload: z.object({
      step: z.number().int().nonnegative(),
      next_agent: z.enum([
        "retrieval",
        "analysis",
        "writer",
        "critic",
        "finish",
      ]),
      objective: z.string(),
      reason: z.string(),
    }),
  }),
  "task.created": eventSchema("task.created"),
  "task.started": eventSchema("task.started"),
  "task.cancellation_requested": eventSchema("task.cancellation_requested"),
  "task.cancelled": eventSchema("task.cancelled"),
  "task.completed": eventSchema("task.completed"),
  "task.failed": eventSchema("task.failed"),
  "task.interrupted": eventSchema("task.interrupted"),
  "stage.started": eventSchema("stage.started"),
  "stage.progress": eventSchema("stage.progress").superRefine((event, context) => {
    if (event.stage === "read" && "total" in event.payload && !readProgressSchema.safeParse(event.payload).success) {
      context.addIssue({ code: "custom", message: "Invalid read progress counts", path: ["payload"] });
    }
  }),
  "stage.warning": eventSchema("stage.warning"),
  "stage.completed": eventSchema("stage.completed"),
  "stage.failed": eventSchema("stage.failed"),
  "plan.available": eventSchema("plan.available"),
  "papers.discovered": eventSchema("papers.discovered"),
  "papers.selected": eventSchema("papers.selected"),
  "paper.read": eventSchema("paper.read"),
  "analysis.available": eventSchema("analysis.available"),
  "draft.available": eventSchema("draft.available"),
  "critique.completed": eventSchema("critique.completed"),
  "evidence.available": eventSchema("evidence.available"),
  "result.available": eventSchema("result.available"),
} as const;

export const allEventTypes = EVENT_TYPES;

export const researchEventSchema = z.discriminatedUnion("event_type", [
  eventSchemas["agent.delegated"],
  eventSchemas["task.created"],
  eventSchemas["task.started"],
  eventSchemas["task.cancellation_requested"],
  eventSchemas["task.cancelled"],
  eventSchemas["task.completed"],
  eventSchemas["task.failed"],
  eventSchemas["task.interrupted"],
  eventSchemas["stage.started"],
  eventSchemas["stage.progress"],
  eventSchemas["stage.warning"],
  eventSchemas["stage.completed"],
  eventSchemas["stage.failed"],
  eventSchemas["plan.available"],
  eventSchemas["papers.discovered"],
  eventSchemas["papers.selected"],
  eventSchemas["paper.read"],
  eventSchemas["analysis.available"],
  eventSchemas["draft.available"],
  eventSchemas["critique.completed"],
  eventSchemas["evidence.available"],
  eventSchemas["result.available"],
]);

const eventEnvelopeSchema = baseEventSchema.extend({ event_type: z.string() });

export function parseResearchEvent(value: unknown): ParseResearchEventResult {
  const parsed = researchEventSchema.safeParse(value);
  if (parsed.success) {
    return {
      status: "accepted",
      event: parsed.data as ResearchEvent,
    };
  }

  const envelope = eventEnvelopeSchema.safeParse(value);
  if (
    envelope.success &&
    !allEventTypes.includes(envelope.data.event_type as EventType)
  ) {
    return { status: "unknown", event: envelope.data, reason: "unknown_event" };
  }
  return { status: "rejected", event: value, reason: "invalid_event" };
}
