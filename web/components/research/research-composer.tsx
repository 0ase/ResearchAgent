"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useRef, useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { z } from "zod";

import { AdvancedSettings } from "@/components/research/advanced-settings";
import { ExampleQueries } from "@/components/research/example-queries";
import { Button } from "@/components/ui/button";
import { InlineAlert } from "@/components/ui/inline-alert";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import { useCreateTask } from "@/features/tasks/hooks/use-create-task";
import type { CreateTaskRequest } from "@/lib/api/client";
import {
  ACADEMIC_SOURCES,
  usePreferencesStore,
} from "@/features/preferences/preferences-store";

const sourceSchema = z.enum(ACADEMIC_SOURCES);

export const researchComposerSchema = z.object({
  query: z.string().trim().min(1).max(2000),
  maxPapers: z.number().int().min(1).max(50),
  sources: z.array(sourceSchema).min(1),
});

export type ResearchComposerValues = z.infer<typeof researchComposerSchema>;
export type CreateTaskResult = {
  task: { id: string };
  links: Record<string, string>;
};

const defaultValues: ResearchComposerValues = {
  query: "",
  maxPapers: 20,
  sources: ["arxiv", "semantic_scholar", "pubmed", "crossref"],
};

export function ResearchComposer({
  onCreated,
  createTask,
}: {
  onCreated?: (taskId: string) => void;
  createTask?: (request: CreateTaskRequest) => Promise<CreateTaskResult>;
}) {
  const locale = useLocale();
  const t = useTranslations();
  const mutation = useCreateTask();
  const requestId = useRef<string | null>(null);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [submitError, setSubmitError] = useState<unknown>(null);
  const [customSubmitting, setCustomSubmitting] = useState(false);
  const researchDefaults = usePreferencesStore((state) => state.research);
  const preferencesHydrated = usePreferencesStore((state) => state.hasHydrated);
  const form = useForm<ResearchComposerValues>({
    resolver: zodResolver(researchComposerSchema),
    defaultValues,
    mode: "onSubmit",
  });
  const formIsDirty = form.formState.isDirty;

  useEffect(() => {
    if (!preferencesHydrated || formIsDirty) return;
    form.reset({
      query: form.getValues("query"),
      maxPapers: researchDefaults.maxPapers,
      sources: researchDefaults.sources,
    });
  }, [form, formIsDirty, preferencesHydrated, researchDefaults]);
  const queryValue = useWatch({ control: form.control, name: "query" });

  const isSubmitting = createTask ? customSubmitting : mutation.isPending;

  async function onSubmit(values: ResearchComposerValues) {
    setSubmitError(null);
    requestId.current ??= createClientRequestId();
    const request: CreateTaskRequest = {
      client_request_id: requestId.current,
      query: values.query,
      options: {
        max_papers: values.maxPapers,
        sources: values.sources,
        output_language: locale === "zh-CN" ? "zh-CN" : "en",
      },
    };

    try {
      if (createTask) setCustomSubmitting(true);
      const response = createTask
        ? await createTask(request)
        : await mutation.mutateAsync(request);
      if (response.task.id) onCreated?.(response.task.id);
    } catch (error) {
      setSubmitError(error);
    } finally {
      if (createTask) setCustomSubmitting(false);
    }
  }

  function handleQueryKeyDown(event: React.KeyboardEvent<HTMLTextAreaElement>) {
    if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
      event.preventDefault();
      void form.handleSubmit(onSubmit)();
    }
  }

  const conflictTaskId = getConflictTaskId(submitError);
  const errors = form.formState.errors;

  return (
    <section className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-6 sm:p-8">
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
          {t("composer.eyebrow")}
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-[var(--color-text)]">
          {t("composer.title")}
        </h1>
        <p className="mt-2 text-sm leading-6 text-[var(--color-text-muted)]">
          {t("composer.description")}
        </p>
      </div>

      {submitError && conflictTaskId ? (
        <InlineAlert tone="warning" className="mt-5">
          {t("composer.conflict")}{" "}
          <a
            className="font-medium underline"
            href={`/research/${encodeURIComponent(conflictTaskId)}`}
          >
            {t("composer.returnToActive")}
          </a>
        </InlineAlert>
      ) : submitError ? (
        <InlineAlert tone="error" className="mt-5">
          {t("composer.createError")}
        </InlineAlert>
      ) : null}

      <form
        className="mt-6"
        onSubmit={(event) => void form.handleSubmit(onSubmit)(event)}
      >
        <label
          htmlFor="research-question"
          className="text-sm font-medium text-[var(--color-text)]"
        >
          {t("composer.questionLabel")}
        </label>
        <Textarea
          id="research-question"
          aria-label={t("composer.questionLabel")}
          aria-invalid={Boolean(errors.query)}
          placeholder={t("composer.questionPlaceholder")}
          {...form.register("query")}
          onKeyDown={handleQueryKeyDown}
        />
        <div className="mt-1 flex justify-between gap-3 text-xs text-[var(--color-text-subtle)]">
          <span>
            {errors.query
              ? errors.query.type === "too_big"
                ? t("composer.questionTooLong")
                : t("composer.questionRequired")
              : t("composer.shortcut")}
          </span>
          <span>{queryValue.length}/2,000</span>
        </div>

        <ExampleQueries
          onSelect={(query) =>
            form.setValue("query", query, {
              shouldDirty: true,
              shouldValidate: true,
            })
          }
        />
        <AdvancedSettings
          open={advancedOpen}
          onToggle={() => setAdvancedOpen((open) => !open)}
          register={form.register}
        />
        {errors.sources?.message ? (
          <p className="mt-2 text-xs text-[var(--color-error)]">
            {t("composer.selectSource")}
          </p>
        ) : null}
        {errors.maxPapers?.message ? (
          <p className="mt-2 text-xs text-[var(--color-error)]">
            {t("composer.maxPapersInvalid")}
          </p>
        ) : null}

        <div className="mt-6 flex items-center justify-between gap-4">
          <p className="text-xs text-[var(--color-text-subtle)]">
            {t("composer.summary")}
          </p>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? t("composer.starting") : t("composer.start")}
          </Button>
        </div>
      </form>
    </section>
  );
}

export function ResearchComposerSkeleton() {
  return (
    <section className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-4 h-8 w-64" />
      <Skeleton className="mt-3 h-4 w-full max-w-xl" />
      <Skeleton className="mt-8 h-32 w-full" />
      <Skeleton className="mt-6 h-9 w-32" />
    </section>
  );
}

function createClientRequestId(): string {
  return (
    globalThis.crypto?.randomUUID?.() ??
    `research-${Date.now()}-${Math.random().toString(16).slice(2)}`
  );
}

function getConflictTaskId(error: unknown): string | null {
  if (!error || typeof error !== "object") return null;
  const candidate = error as { status?: number; details?: unknown };
  if (
    candidate.status !== 409 ||
    !candidate.details ||
    typeof candidate.details !== "object"
  )
    return null;
  const taskId = (candidate.details as { task_id?: unknown }).task_id;
  return typeof taskId === "string" ? taskId : null;
}
