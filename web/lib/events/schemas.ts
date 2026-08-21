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

function eventSchema<T extends EventType>(eventType: T) {
  return baseEventSchema.extend({ event_type: z.literal(eventType) });
}

export const eventSchemas = {
  "task.created": eventSchema("task.created"),
  "task.started": eventSchema("task.started"),
  "task.cancellation_requested": eventSchema("task.cancellation_requested"),
  "task.cancelled": eventSchema("task.cancelled"),
  "task.completed": eventSchema("task.completed"),
  "task.failed": eventSchema("task.failed"),
  "task.interrupted": eventSchema("task.interrupted"),
  "stage.started": eventSchema("stage.started"),
  "stage.progress": eventSchema("stage.progress"),
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
