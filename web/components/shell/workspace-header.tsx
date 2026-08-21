"use client";

import { PanelRightClose, PanelRightOpen } from "lucide-react";
import { useTranslations } from "next-intl";

import {
  CancelTaskDialog,
  useCancelDialogState,
} from "@/components/research/cancel-task-dialog";
import { LanguageSwitcher } from "@/components/shell/language-switcher";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useCancelTask } from "@/features/tasks/hooks/use-cancel-task";
import { useTask } from "@/features/tasks/hooks/use-task";
import { useUiStore } from "@/stores/ui-store";

export function WorkspaceHeader({ taskId }: { taskId?: string }) {
  const t = useTranslations();
  const isContextPanelOpen = useUiStore((state) => state.isContextPanelOpen);
  const toggleContextPanel = useUiStore((state) => state.toggleContextPanel);
  const taskQuery = useTask(taskId ?? "");
  const cancelMutation = useCancelTask(taskId ?? "");
  const cancelDialog = useCancelDialogState();
  const canCancel =
    taskQuery.data?.available_actions?.includes("cancel") ?? false;

  return (
    <header className="flex min-h-14 items-center justify-between gap-4 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-5">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <h1 className="truncate text-sm font-semibold text-[var(--color-text)]">
            {taskId
              ? (taskQuery.data?.title ?? t("task.researchTask"))
              : t("common.newResearch")}
          </h1>
          {taskId ? <Badge variant="blue">{t("task.workspace")}</Badge> : null}
        </div>
        {taskId ? (
          <p className="truncate text-xs text-[var(--color-text-muted)]">
            {taskQuery.data?.query ?? taskId}
            <span className="ml-2 text-[var(--color-text-subtle)]">
              {t("common.taskId")}: {taskId}
            </span>
          </p>
        ) : null}
      </div>

      <div className="flex items-center gap-1">
        {canCancel ? (
          <Button
            aria-label={t("common.cancelTask")}
            onClick={() => cancelDialog.setOpen(true)}
            variant="ghost"
            disabled={
              cancelMutation.isPending ||
              taskQuery.data?.status === "cancelling"
            }
          >
            {t("common.cancelTask")}
          </Button>
        ) : null}
        <Button
          aria-label={
            isContextPanelOpen
              ? t("common.collapseContext")
              : t("common.expandContext")
          }
          onClick={toggleContextPanel}
          size="icon"
          variant="ghost"
        >
          {isContextPanelOpen ? (
            <PanelRightClose aria-hidden="true" className="h-4 w-4" />
          ) : (
            <PanelRightOpen aria-hidden="true" className="h-4 w-4" />
          )}
        </Button>
        <LanguageSwitcher locked={Boolean(taskId)} />
        <CancelTaskDialog
          open={cancelDialog.open}
          onOpenChange={cancelDialog.setOpen}
          pending={cancelMutation.isPending}
          onConfirm={async () => {
            await cancelMutation.mutateAsync();
          }}
        />
      </div>
    </header>
  );
}
