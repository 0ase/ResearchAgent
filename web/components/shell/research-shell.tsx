"use client";

import type { ReactNode } from "react";
import { useTranslations } from "next-intl";

import { ContextPanel } from "@/components/shell/context-panel";
import { TaskSidebar } from "@/components/shell/task-sidebar";
import { WorkspaceHeader } from "@/components/shell/workspace-header";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/stores/ui-store";

export function ResearchShell({
  children,
  taskId,
}: {
  children: ReactNode;
  taskId?: string;
}) {
  const t = useTranslations("common");
  const isContextPanelOpen = useUiStore((state) => state.isContextPanelOpen);
  const toggleContextPanel = useUiStore((state) => state.toggleContextPanel);

  return (
    <div
      className={[
        "grid h-[100dvh] min-w-[1180px] overflow-x-auto bg-[var(--color-page)]",
        isContextPanelOpen
          ? "grid-cols-[clamp(240px,18.3vw,264px)_minmax(0,1fr)_clamp(320px,25.5vw,368px)]"
          : "grid-cols-[clamp(240px,18.3vw,264px)_minmax(0,1fr)_48px]",
      ].join(" ")}
    >
      <TaskSidebar taskId={taskId} />
      <main className="flex min-h-0 min-w-0 flex-col overflow-hidden">
        <WorkspaceHeader taskId={taskId} />
        <div className="min-h-0 flex-1 overflow-y-auto">{children}</div>
      </main>
      {isContextPanelOpen ? (
        <ContextPanel taskId={taskId} />
      ) : (
        <aside
          aria-label={t("expandContext")}
          className="flex min-h-0 items-start justify-center border-l border-[var(--color-border)] bg-[var(--color-surface)] pt-3"
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
