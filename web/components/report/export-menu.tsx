"use client";

import {
  useTaskExport,
  type ExportFormat,
} from "@/features/export/use-task-export";
import { useTranslations } from "next-intl";

export function ExportMenu({
  taskId,
  onExport,
}: {
  taskId: string;
  onExport?: (format: ExportFormat) => Promise<void> | void;
}) {
  const t = useTranslations("report");
  const exportTask = useTaskExport(taskId);
  async function handleExport(format: ExportFormat) {
    if (onExport) return onExport(format);
    return exportTask.download(format);
  }

  return (
    <div className="relative">
      <details>
        <summary
          role="button"
          className="inline-flex h-9 cursor-pointer list-none items-center rounded-[var(--radius-control)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3 text-[13px] font-medium text-[var(--color-text)]"
        >
          {t("exportMenu")}
        </summary>
        <div
          role="menu"
          className="absolute right-0 z-10 mt-1 min-w-36 rounded-[var(--radius-float)] border border-[var(--color-border)] bg-[var(--color-surface)] p-1 shadow-[var(--shadow-float)]"
        >
          {(["markdown", "bibtex", "json"] as const).map((format) => (
            <button
              key={format}
              type="button"
              role="menuitem"
              disabled={exportTask.isExporting}
              className="block w-full rounded-[var(--radius-control)] px-2 py-1.5 text-left text-[13px] text-[var(--color-text-muted)] hover:bg-[var(--color-surface-subtle)]"
              onClick={() => void handleExport(format)}
            >
              {format === "markdown"
                ? "Markdown"
                : format === "bibtex"
                  ? "BibTeX"
                  : "JSON"}
            </button>
          ))}
        </div>
      </details>
    </div>
  );
}
