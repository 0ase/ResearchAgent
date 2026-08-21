"use client";

import { useTranslations } from "next-intl";

import { HistoryList } from "@/components/history/history-list";
import { EmptyState } from "@/components/ui/empty-state";
import { InlineAlert } from "@/components/ui/inline-alert";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useDeleteTask,
  useHistory,
  useRenameTask,
} from "@/features/history/hooks/use-history";
import { Link } from "@/i18n/navigation";

export default function HistoryPage() {
  const t = useTranslations();
  const history = useHistory(100);
  const renameMutation = useRenameTask();
  const deleteMutation = useDeleteTask();
  const tasks = history.data ?? [];
  const activeTaskId = tasks.find((task) =>
    ["queued", "running", "cancelling"].includes(task.status),
  )?.id;

  return (
    <main className="min-h-screen bg-[var(--color-page)] px-8 py-10">
      <div className="mx-auto max-w-5xl">
        <p className="text-xs font-medium uppercase tracking-[0.08em] text-[var(--color-text-subtle)]">
          {t("common.brand")}
        </p>
        <div className="mt-2 flex items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold text-[var(--color-text)]">
              {t("history.title")}
            </h1>
            <p className="mt-1 text-sm text-[var(--color-text-muted)]">
              {t("history.description")}
            </p>
          </div>
          <Link
            href="/"
            className="text-sm font-medium text-[var(--color-primary)] hover:text-[var(--color-primary-hover)]"
          >
            {t("navigation.newResearch")}
          </Link>
        </div>
        <div className="mt-8">
          {history.isPending ? (
            <div className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-20 w-full" />
              <Skeleton className="h-20 w-full" />
            </div>
          ) : null}
          {history.isError ? (
            <InlineAlert tone="error">{t("history.loadError")}</InlineAlert>
          ) : null}
          {!history.isPending && !history.isError && !tasks.length ? (
            <EmptyState
              title={t("history.emptyTitle")}
              description={t("history.emptyDescription")}
              action={
                <Link
                  href="/"
                  className="text-sm font-medium text-[var(--color-primary)]"
                >
                  {t("history.createFirst")}
                </Link>
              }
            />
          ) : null}
          {!history.isPending && !history.isError && tasks.length ? (
            <HistoryList
              tasks={tasks}
              activeTaskId={activeTaskId}
              onRename={async (taskId, title) => {
                await renameMutation.mutateAsync({ taskId, title });
              }}
              onDelete={async (taskId) => {
                await deleteMutation.mutateAsync(taskId);
              }}
            />
          ) : null}
        </div>
      </div>
    </main>
  );
}
