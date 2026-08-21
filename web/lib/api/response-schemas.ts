import { z } from "zod";

import type { components } from "@/lib/api/schema";

const taskStatusSchema = z.enum([
  "queued",
  "running",
  "cancelling",
  "completed",
  "failed",
  "cancelled",
  "interrupted",
]);
const stageSchema = z.enum([
  "orchestrate",
  "search",
  "filter",
  "read",
  "analyze",
  "synthesize",
  "critic",
]);
const stageStatusSchema = z.enum([
  "pending",
  "running",
  "completed",
  "warning",
  "failed",
  "cancelled",
]);

const taskProgressSchema = z.object({
  message: z.string().nullable().optional(),
  metrics: z.record(z.string(), z.unknown()).optional(),
});

const stageSnapshotSchema = z.object({
  stage: stageSchema,
  status: stageStatusSchema,
  started_at: z.string().datetime({ offset: true }).nullable().optional(),
  completed_at: z.string().datetime({ offset: true }).nullable().optional(),
  duration_ms: z.number().int().nonnegative().nullable().optional(),
  detail: z.string().nullable().optional(),
  attempt: z.number().int().positive(),
});

export const taskSnapshotSchema = z
  .object({
    id: z.string().min(1),
    parent_task_id: z.string().nullable().optional(),
    client_request_id: z.string().min(1),
    query: z.string(),
    title: z.string(),
    status: taskStatusSchema,
    effective_locale: z.enum(["zh-CN", "en"]),
    current_stage: stageSchema.nullable().optional(),
    options: z.record(z.string(), z.unknown()).optional(),
    progress: taskProgressSchema.optional(),
    stages: z.array(stageSnapshotSchema).optional(),
    statistics: z.record(z.string(), z.unknown()).optional(),
    last_sequence: z.number().int().nonnegative(),
    available_actions: z.array(z.string()).optional(),
    created_at: z.string().datetime({ offset: true }),
    started_at: z.string().datetime({ offset: true }).nullable().optional(),
    completed_at: z.string().datetime({ offset: true }).nullable().optional(),
    error_code: z.string().nullable().optional(),
    error_message: z.string().nullable().optional(),
  })
  .passthrough() satisfies z.ZodType<components["schemas"]["TaskSnapshot"]>;

export const createTaskResponseSchema = z
  .object({
    task: taskSnapshotSchema,
    links: z.object({
      self: z.string(),
      events: z.string(),
      result: z.string(),
    }),
  })
  .passthrough();

const paperSchema = z
  .object({
    paper_id: z.string(),
    canonical_id: z.string().nullable().optional(),
    title: z.string(),
    authors: z.array(z.string()).optional(),
    abstract: z.string().nullable().optional(),
    source: z.string(),
    source_id: z.string(),
    doi: z.string().nullable().optional(),
    year: z.number().int().nullable().optional(),
    citation_count: z.number().int().nullable().optional(),
    pdf_url: z.string().nullable().optional(),
    landing_page_url: z.string().nullable().optional(),
    relevance_score: z.number().nullable().optional(),
    relevance_reason: z.string().nullable().optional(),
    selected: z.boolean().optional(),
  })
  .passthrough();

const claimSchema = z
  .object({
    claim_id: z.string(),
    paper_id: z.string(),
    statement: z.string(),
    support_type: z.string(),
    chunk_ids: z.array(z.string()).optional(),
    evidence_text: z.string().nullable().optional(),
    valid: z.boolean(),
  })
  .passthrough();

const findingSchema = z
  .object({
    finding_id: z.string(),
    kind: z.string(),
    statement: z.string(),
    claim_ids: z.array(z.string()).optional(),
    paper_ids: z.array(z.string()).optional(),
    support_type: z.string(),
    valid: z.boolean(),
  })
  .passthrough();

const evidenceSchema = z
  .object({
    evidence_id: z.string(),
    task_id: z.string(),
    paper_id: z.string(),
    chunk_id: z.string(),
    claim_id: z.string().nullable().optional(),
    excerpt: z.string(),
    content_type: z.string(),
    page_start: z.number().int().nullable().optional(),
    page_end: z.number().int().nullable().optional(),
    support_type: z.string(),
    verified: z.boolean(),
    validation_message: z.string().nullable().optional(),
  })
  .passthrough();

const citationSchema = z
  .object({
    citation_id: z.string(),
    section_id: z.string(),
    paper_id: z.string(),
    claim_ids: z.array(z.string()).optional(),
    chunk_ids: z.array(z.string()).optional(),
    evidence_ids: z.array(z.string()).optional(),
    display_number: z.number().int().nullable().optional(),
    valid: z.boolean(),
    support_type: z.string(),
    validation_message: z.string().nullable().optional(),
  })
  .passthrough();

const reportSectionSchema = z
  .object({
    section_id: z.string(),
    heading: z.string(),
    level: z.number().int(),
    markdown: z.string(),
    citation_ids: z.array(z.string()).optional(),
  })
  .passthrough();

const structuredReportSchema = z
  .object({
    version: z.number().int(),
    markdown: z.string(),
    sections: z.array(reportSectionSchema).optional(),
    citations: z.array(citationSchema).optional(),
  })
  .passthrough();

export const researchResultSchema = z
  .object({
    task_id: z.string(),
    report_markdown: z.string(),
    research_plan: z.array(z.record(z.string(), z.unknown())).optional(),
    papers: z.array(paperSchema).optional(),
    paper_insights: z.array(z.record(z.string(), z.unknown())).optional(),
    paper_claims: z.array(claimSchema).optional(),
    analysis_findings: z.array(findingSchema).optional(),
    structured_report: structuredReportSchema.optional(),
    analysis: z.record(z.string(), z.unknown()).optional(),
    critique: z.record(z.string(), z.unknown()).optional(),
    statistics: z.record(z.string(), z.unknown()).optional(),
    evidence: z.array(evidenceSchema).optional(),
    citations: z.array(citationSchema).optional(),
    partial: z.boolean(),
    warnings: z.array(z.string()).optional(),
    capabilities: z.object({
      supports_replay: z.boolean(),
      supports_evidence: z.boolean(),
      supports_structured_papers: z.boolean(),
    }),
  })
  .passthrough();

export const taskHistorySchema = z.array(taskSnapshotSchema);
export const emptyResponseSchema = z.undefined();
export const deepSeekSettingsSchema = z.object({
  provider: z.literal("deepseek"),
  default_model: z.string().min(1),
  api_key_required: z.boolean(),
  api_key_configured: z.boolean(),
});

export type TaskSnapshotValue = z.infer<typeof taskSnapshotSchema>;
export type ResearchResultValue = z.infer<typeof researchResultSchema>;
