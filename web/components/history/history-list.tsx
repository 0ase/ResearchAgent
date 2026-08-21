"use client";

import { useMemo, useState } from "react";
import { useLocale, useTranslations } from "next-intl";

import { DeleteTaskDialog } from "@/components/history/delete-task-dialog";
import {
  HistoryFilters,
  type HistorySort,
} from "@/components/history/history-filters";
import { RenameTaskDialog } from "@/components/history/rename-task-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { TaskSnapshotResponse } from "@/lib/api/client";
import { Link } from "@/i18n/navigation";
import { taskStatusMessageKeys } from "@/i18n/task-labels";
import type { TaskStatus } from "@/lib/events/types";

const activeStatuses = new Set(["queued", "running", "cancelling"]);

export function HistoryList({
  tasks,
  activeTaskId,
  onRename,
  onDelete,
}: {
  tasks: TaskSnapshotResponse[];
  activeTaskId?: string | null;
  onRename?: (taskId: string, title: string) => Promise<void> | void;
  onDelete?: (taskId: string) => Promise<void> | void;
}) {
  const t = useTranslations();
  const taskT = useTranslations("task");
  const locale = useLocale();
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("all");
  const [sort, setSort] = useState<HistorySort>("recent");
  const [renameTask, setRenameTask] = useState<TaskSnapshotResponse | null>(
    null,
  );
  const [deleteTask, setDeleteTask] = useState<TaskSnapshotResponse | null>(
    null,
  );
  const visibleTasks = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return tasks
      .filter((task) => status === "all" || task.status === status)
      .filter(
        (task) =>
          !needle ||
          `${task.title} ${task.query}`.toLowerCase().includes(needle),
      )
      .sort((left, right) =>
        sort === "score"
          ? scoreOf(right) - scoreOf(left)
          : right.created_at.localeCompare(left.created_at),
      );
  }, [query, sort, status, tasks]);

  return (
    <section aria-label={t("history.list")} className="space-y-4">
      <HistoryFilters
        query={query}
        status={status}
        sort={sort}
        onQueryChange={setQuery}
        onStatusChange={setStatus}
        onSortChange={setSort}
      />
      <div className="divide-y divide-[var(--color-border)] border-b border-[var(--color-border)]">
        {visibleTasks.map((task) => {
          const isActive =
            task.id === activeTaskId || activeStatuses.has(task.status);
          return (
            <article
              key={task.id}
              className="flex items-start justify-between gap-4 py-4"
            >
              <div className="min-w-0">
                <Link
                  href={`/research/${encodeURIComponent(task.id)}`}
                  className="font-medium text-[var(--color-text)] hover:text-[var(--color-primary)]"
                >
                  {task.title}
                </Link>
                <p className="mt-1 line-clamp-2 text-sm text-[var(--color-text-muted)]">
                  {task.query}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-[var(--color-text-subtle)]">
                  <Badge
                    variant={
                      task.status === "completed"
                        ? "success"
                        : task.status === "failed"
                          ? "error"
                          : "neutral"
                    }
                  >
                    {taskT(taskStatusMessageKeys[task.status as TaskStatus])}
                  </Badge>
                  <span>{formatDate(task.created_at, locale)}</span>
                  <span>
                    {numberFrom(task.statistics?.papers_count) == null
                      ? t("history.statisticsUnavailable")
                      : t("history.papersCount", {
                          count: numberFrom(
                            task.statistics?.papers_count,
                          ) as number,
                        })}
                  </span>
                  {scoreOf(task) ? (
                    <span>
                      {t("history.score", { value: scoreOf(task).toFixed(2) })}
                    </span>
                  ) : null}
                </div>
              </div>
              <div className="flex shrink-0 items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t("history.renameTask", { title: task.title })}
                  onClick={() => setRenameTask(task)}
                  disabled={
                    !task.available_actions?.includes("rename") &&
                    !task.available_actions?.includes("update")
                  }
                >
                  {t("common.rename")}
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  aria-label={t("history.deleteTask", { title: task.title })}
                  onClick={() => setDeleteTask(task)}
                  disabled={
                    isActive ||
                    task.status === "queued" ||
                    !task.available_actions?.includes("delete")
                  }
                >
                  {t("common.delete")}
                </Button>
              </div>
            </article>
          );
        })}
      </div>
      {!visibleTasks.length ? (
        <p className="py-8 text-center text-sm text-[var(--color-text-muted)]">
          {t("history.noMatches")}
        </p>
      ) : null}
      <RenameTaskDialog
        task={renameTask}
        open={Boolean(renameTask)}
        onOpenChange={(open) => {
          if (!open) setRenameTask(null);
        }}
        onConfirm={async (title) => {
          if (renameTask) await onRename?.(renameTask.id, title);
        }}
      />
      <DeleteTaskDialog
        task={deleteTask}
        open={Boolean(deleteTask)}
        onOpenChange={(open) => {
          if (!open) setDeleteTask(null);
        }}
        onConfirm={async () => {
          if (deleteTask) await onDelete?.(deleteTask.id);
        }}
      />
    </section>
  );
}

function scoreOf(task: TaskSnapshotResponse): number {
  return numberFrom(task.statistics?.critique_score) ?? 0;
}

function numberFrom(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function formatDate(value: string, locale: string): string {
  return new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(
    new Date(value),
  );
}
