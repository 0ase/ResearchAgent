"use client";

import { useState } from "react";

import { getApiBaseUrl } from "@/lib/api/client";

export type ExportFormat = "markdown" | "bibtex" | "json";

export function useTaskExport(taskId: string) {
  const [isExporting, setIsExporting] = useState(false);

  async function download(format: ExportFormat) {
    setIsExporting(true);
    try {
      const response = await fetch(
        `${getApiBaseUrl()}/api/v1/research/tasks/${encodeURIComponent(taskId)}/export?format=${format}`,
        { headers: { Accept: "application/octet-stream" } },
      );
      if (!response.ok)
        throw new Error(`Export failed with status ${response.status}`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `research-${taskId}.${format === "markdown" ? "md" : format === "bibtex" ? "bib" : "json"}`;
      anchor.click();
      URL.revokeObjectURL(url);
    } finally {
      setIsExporting(false);
    }
  }

  return { download, isExporting };
}
