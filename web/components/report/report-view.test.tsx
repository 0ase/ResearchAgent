import { userEvent } from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { Providers } from "@/app/providers";
import { ExportMenu } from "@/components/report/export-menu";
import { ReportView } from "@/components/report/report-view";
import type { ResearchTaskResultResponse } from "@/lib/api/client";
import { resetUiStore, useUiStore } from "@/stores/ui-store";

const result: ResearchTaskResultResponse = {
  task_id: "task-report",
  report_markdown: `# Overview

## Findings

| Method | Result |
| --- | --- |
| RAG | Better grounding |

See [[CITE:paper-1]] and [the source](https://example.com/paper).

<script>window.__bad = true</script>`,
  research_plan: [],
  papers: [],
  paper_insights: [],
  analysis: {},
  critique: { attempt: 2, summary: "Final round passed" },
  statistics: { papers_read: 4, duration_ms: 1200 },
  evidence: [],
  citations: [],
  partial: true,
  warnings: ["Crossref was unavailable"],
  capabilities: {
    supports_replay: true,
    supports_evidence: false,
    supports_structured_papers: false,
  },
};

describe("ReportView", () => {
  beforeEach(() => resetUiStore());

  it("renders Markdown headings, a GFM table, a stable TOC, and safe citations", () => {
    render(
      <Providers locale="en">
        <ReportView taskId="task-report" result={result} />
      </Providers>,
    );

    expect(screen.getByRole("heading", { name: "Overview" })).toHaveAttribute(
      "id",
      "overview",
    );
    expect(screen.getByRole("heading", { name: "Findings" })).toHaveAttribute(
      "id",
      "findings",
    );
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Overview" })).toHaveAttribute(
      "href",
      "#overview",
    );
    expect(screen.getByText("Citation: paper-1")).toBeInTheDocument();
    expect(screen.queryByText("window.__bad = true")).not.toBeInTheDocument();
  });

  it("marks partial results with warnings and secures external links", () => {
    render(
      <Providers locale="en">
        <ReportView taskId="task-report" result={result} />
      </Providers>,
    );

    expect(screen.getByRole("alert")).toHaveTextContent(
      "Crossref was unavailable",
    );
    expect(screen.getByRole("link", { name: "the source" })).toHaveAttribute(
      "target",
      "_blank",
    );
    expect(screen.getByRole("link", { name: "the source" })).toHaveAttribute(
      "rel",
      "noreferrer noopener",
    );
    expect(screen.getByText(/final round passed/i)).toBeInTheDocument();
  });

  it("uses a backend export action for Markdown, BibTeX, and JSON", async () => {
    const user = userEvent.setup();
    const onExport = vi.fn(async () => undefined);
    render(
      <Providers locale="en">
        <ExportMenu taskId="task-report" onExport={onExport} />
      </Providers>,
    );

    await user.click(screen.getByRole("button", { name: /export report/i }));
    await user.click(screen.getByRole("menuitem", { name: /bibtex/i }));

    expect(onExport).toHaveBeenCalledWith("bibtex");
  });

  it("syncs a selected paper to the context panel state", async () => {
    const user = userEvent.setup();
    const paperResult = {
      ...result,
      papers: [
        {
          paper_id: "paper-1",
          title: "Paper one",
          source: "arxiv",
          authors: ["Researcher"],
          abstract: "Paper abstract",
        },
      ],
    } as ResearchTaskResultResponse;
    render(
      <Providers locale="en">
        <ReportView taskId="task-report" result={paperResult} />
      </Providers>,
    );

    await user.click(screen.getByRole("tab", { name: /papers \(1\)/i }));
    await user.click(screen.getByRole("button", { name: /paper: paper one/i }));

    expect(useUiStore.getState().selectedObjectId).toBe("paper-1");
    expect(useUiStore.getState().contextTab).toBe("papers");
  });
});
