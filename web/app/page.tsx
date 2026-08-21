"use client";

import { useTranslations } from "next-intl";
import { ArrowRight } from "lucide-react";

import {
  ResearchComposer,
  ResearchComposerSkeleton,
} from "@/components/research/research-composer";
import { ResearchShell } from "@/components/shell/research-shell";
import { InlineAlert } from "@/components/ui/inline-alert";
import { useActiveTask } from "@/features/tasks/hooks/use-active-task";
import { Link, useRouter } from "@/i18n/navigation";
import { taskStatusMessageKeys } from "@/i18n/task-labels";

export default function Home() {
  const router = useRouter();
  const t = useTranslations();
  const activeTask = useActiveTask();

  return (
    <ResearchShell>
      <div className="mx-auto flex min-h-full w-full max-w-4xl flex-col justify-center px-8 py-12">
        {activeTask.isPending ? <ResearchComposerSkeleton /> : null}
        {!activeTask.isPending && activeTask.data ? (
          <ActiveTaskSummary task={activeTask.data} />
        ) : null}
        {!activeTask.isPending && !activeTask.data ? (
          <>
            {activeTask.isError ? (
              <InlineAlert tone="warning" className="mb-4">
                {t("composer.activeUnavailable")}
              </InlineAlert>
            ) : null}
            <ResearchComposer
              onCreated={(taskId) =>
                router.push(`/research/${encodeURIComponent(taskId)}`)
              }
            />
          </>
        ) : null}
      </div>
    </ResearchShell>
  );
}

function ActiveTaskSummary({
  task,
}: {
  task: {
    id: string;
    title: string;
    query: string;
    status: keyof typeof taskStatusMessageKeys;
  };
}) {
  const t = useTranslations();
  const taskT = useTranslations("task");
  return (
    <section className="rounded-[var(--radius-panel)] border border-[var(--color-border)] bg-[var(--color-surface)] p-8">
      <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-primary)]">
        {t("task.activeResearch")}
      </p>
      <h1 className="mt-3 text-2xl font-semibold tracking-tight text-[var(--color-text)]">
        {task.title}
      </h1>
      <p className="mt-3 text-[15px] leading-7 text-[var(--color-text-muted)]">
        {task.query}
      </p>
      <p className="mt-4 text-xs text-[var(--color-text-subtle)]">
        {taskT("statusLabel")}: {taskT(taskStatusMessageKeys[task.status])}
      </p>
      <Link
        href={`/research/${encodeURIComponent(task.id)}`}
        className="mt-6 inline-flex h-9 items-center gap-2 rounded-[var(--radius-control)] bg-[var(--color-primary)] px-3 text-[13px] font-medium text-white hover:bg-[var(--color-primary-hover)]"
      >
        {t("task.returnToTask")}
        <ArrowRight aria-hidden="true" className="h-4 w-4" />
      </Link>
    </section>
  );
}
