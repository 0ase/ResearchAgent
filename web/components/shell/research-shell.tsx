"use client";

import { useEffect, type ReactNode } from "react";
import { useTranslations } from "next-intl";

import { ContextPanel } from "@/components/shell/context-panel";
import { TaskSidebar } from "@/components/shell/task-sidebar";
import { WorkspaceHeader } from "@/components/shell/workspace-header";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/stores/ui-store";
import { TaskConversation } from "@/components/research/task-conversation";
import { TaskEventsProvider } from "@/features/tasks/hooks/use-task-events";
import { TaskCancellationProvider } from "@/components/research/task-cancellation";

export function ResearchShell({
  children, taskId,
}: { children: ReactNode; taskId?: string }) {
  const content = <ResearchShellLayout taskId={taskId}>{children}</ResearchShellLayout>;
  return taskId ? <TaskEventsProvider taskId={taskId}><TaskCancellationProvider key={taskId} taskId={taskId}>{content}</TaskCancellationProvider></TaskEventsProvider> : content;
}

function ResearchShellLayout({
  children,
  taskId,
}: {
  children: ReactNode;
  taskId?: string;
}) {
  const t = useTranslations("common");
  const isTaskSidebarOpen = useUiStore((state) => state.isTaskSidebarOpen);
  const isContextPanelOpen = useUiStore((state) => state.isContextPanelOpen);
  const toggleContextPanel = useUiStore((state) => state.toggleContextPanel);
  const gridColumns = isTaskSidebarOpen
    ? isContextPanelOpen
      ? "grid-cols-[clamp(240px,18.3vw,264px)_minmax(0,1fr)_clamp(320px,25.5vw,368px)]"
      : "grid-cols-[clamp(240px,18.3vw,264px)_minmax(0,1fr)_48px]"
    : isContextPanelOpen
      ? "grid-cols-[minmax(0,1fr)_clamp(320px,25.5vw,368px)]"
      : "grid-cols-[minmax(0,1fr)_48px]";

  useEffect(() => {
    void useUiStore.persist.rehydrate();
  }, []);

  return (
    <div
      className={[
        "grid h-[100dvh] min-w-[1180px] overflow-x-auto bg-[var(--color-page)]",
        gridColumns,
      ].join(" ")}
    >
      {isTaskSidebarOpen ? <TaskSidebar taskId={taskId} /> : null}
      <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
        <WorkspaceHeader taskId={taskId} />
        {taskId ? <TaskConversation key={taskId} taskId={taskId}>{children}</TaskConversation> : <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>}
      </main>
      {isContextPanelOpen ? (
        <ContextPanel taskId={taskId} />
      ) : (
        <aside
          aria-label={t("expandContext")}
          className="flex min-h-0 items-start justify-center border-l border-[var(--color-border)] bg-[var(--color-chrome)] pt-3"
        >
          <Button
            aria-label={t("expandContext")}
            onClick={toggleContextPanel}
            size="icon"
            variant="ghost"
          >
            <span aria-hidden="true">‹</span>
          </Button>
        </aside>
      )}
    </div>
  );
}
