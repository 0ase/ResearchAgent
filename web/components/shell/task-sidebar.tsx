"use client";

import { Clock3, FlaskConical, Home, Plus } from "lucide-react";
import { useTranslations } from "next-intl";

import { buttonVariants } from "@/components/ui/button";
import { useHistory } from "@/features/history/hooks/use-history";
import { cn } from "@/lib/utils/cn";
import { Link } from "@/i18n/navigation";

export function TaskSidebar({ taskId }: { taskId?: string }) {
  const t = useTranslations();
  const history = useHistory(20);

  return (
    <aside
      aria-label={t("navigation.taskNavigation")}
      className="flex min-h-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]"
    >
      <div className="flex h-14 items-center gap-2 border-b border-[var(--color-border)] px-4">
        <span className="flex h-7 w-7 items-center justify-center rounded-[var(--radius-control)] bg-[var(--color-primary)] text-white">
          <FlaskConical aria-hidden="true" className="h-4 w-4" />
        </span>
        <span className="text-sm font-semibold text-[var(--color-text)]">
          {t("common.brand")}
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <Link
          href="/"
          className={cn(
            buttonVariants({ variant: "secondary" }),
            "mb-4 w-full justify-start",
          )}
        >
          <Plus aria-hidden="true" className="h-4 w-4" />
          {t("navigation.newResearch")}
        </Link>

        <nav aria-label={t("navigation.workspaceLinks")} className="space-y-1">
          <Link
            href="/"
            className="flex h-9 items-center gap-2 rounded-[var(--radius-control)] px-2.5 text-[13px] font-medium text-[var(--color-text-muted)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text)]"
          >
            <Home aria-hidden="true" className="h-4 w-4" />
            {t("navigation.home")}
          </Link>
          <Link
            href="/history"
            className="flex h-9 items-center gap-2 rounded-[var(--radius-control)] px-2.5 text-[13px] font-medium text-[var(--color-text-muted)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text)]"
          >
            <Clock3 aria-hidden="true" className="h-4 w-4" />
            {t("navigation.history")}
          </Link>
        </nav>

        {taskId ? (
          <div className="mt-6 border-t border-[var(--color-border)] pt-4">
            <p className="px-2.5 text-[11px] font-medium uppercase tracking-[0.08em] text-[var(--color-text-subtle)]">
              {t("navigation.currentTask")}
            </p>
            <Link
              href={`/research/${encodeURIComponent(taskId)}`}
              className="mt-2 block truncate rounded-[var(--radius-control)] bg-[var(--color-primary-subtle)] px-2.5 py-2 text-xs text-[var(--color-primary-hover)]"
            >
              {taskId}
            </Link>
          </div>
        ) : null}

        {history.data?.length ? (
          <div className="mt-6 border-t border-[var(--color-border)] pt-4">
            <p className="px-2.5 text-[11px] font-medium uppercase tracking-[0.08em] text-[var(--color-text-subtle)]">
              {t("navigation.recentResearch")}
            </p>
            <nav
              aria-label={t("navigation.recentResearch")}
              className="mt-2 space-y-1"
            >
              {history.data.slice(0, 20).map((task) => (
                <Link
                  key={task.id}
                  href={`/research/${encodeURIComponent(task.id)}`}
                  className="block truncate rounded-[var(--radius-control)] px-2.5 py-2 text-xs text-[var(--color-text-muted)] hover:bg-[var(--color-surface-subtle)] hover:text-[var(--color-text)]"
                >
                  {task.title}
                </Link>
              ))}
            </nav>
          </div>
        ) : null}
      </div>

      <div className="border-t border-[var(--color-border)] px-4 py-3 text-xs text-[var(--color-text-subtle)]">
        {t("navigation.multiSourceWorkspace")}
      </div>
    </aside>
  );
}
