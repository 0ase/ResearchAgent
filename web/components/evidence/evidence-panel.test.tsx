import { userEvent } from "@testing-library/user-event";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach } from "vitest";

import { CitationMarker } from "@/components/report/citation-marker";
import { EvidencePanel } from "@/components/evidence/evidence-panel";
import type { ResearchTaskResultResponse } from "@/lib/api/client";
import { resetUiStore, useUiStore } from "@/stores/ui-store";
import { Providers } from "@/app/providers";

const result = {
  task_id: "task-1",
  report_markdown: "# Report",
  partial: false,
  papers: [{ paper_id: "paper-1", title: "A source paper" }],
  citations: [
    {
      citation_id: "citation-1",
      display_number: 3,
      valid: true,
      evidence_ids: ["evidence-1"],
    },
  ],
  evidence: [
    {
      evidence_id: "evidence-1",
      paper_id: "paper-1",
      excerpt: "Exact source text",
      content_type: "pdf",
      page_start: 4,
      page_end: 5,
      verified: true,
    },
  ],
  capabilities: {
    supports_evidence: true,
    supports_replay: true,
    supports_structured_papers: true,
  },
} as unknown as ResearchTaskResultResponse;

describe("EvidencePanel", () => {
  beforeEach(() => resetUiStore());

  it("opens linked evidence from a citation marker", async () => {
    const user = userEvent.setup();
    render(
      <Providers locale="en">
        <>
          <CitationMarker citationId="citation-1" displayNumber={3} />
          <EvidencePanel result={result} />
        </>
      </Providers>,
    );

    await user.click(screen.getByRole("button", { name: /open citation 3/i }));

    expect(screen.getByText("Exact source text")).toBeInTheDocument();
    expect(screen.getByText("Page 4–5")).toBeInTheDocument();
    expect(useUiStore.getState().selectedObjectId).toBe("citation-1");
  });

  it("links persisted evidence through a shared chunk id", async () => {
    const user = userEvent.setup();
    const chunkLinkedResult = {
      ...result,
      citations: [
        {
          ...result.citations?.[0],
          evidence_ids: [],
          chunk_ids: ["chunk-1"],
        },
      ],
      evidence: [
        {
          ...result.evidence?.[0],
          chunk_id: "chunk-1",
        },
      ],
    } as ResearchTaskResultResponse;
    render(
      <Providers locale="en">
        <>
          <CitationMarker citationId="citation-1" displayNumber={3} />
          <EvidencePanel result={chunkLinkedResult} />
        </>
      </Providers>,
    );

    await user.click(screen.getByRole("button", { name: /open citation 3/i }));

    expect(screen.getByText("Exact source text")).toBeInTheDocument();
  });

  it("shows an unverified warning and routes to paper details", async () => {
    const user = userEvent.setup();
    const unverified = {
      ...result,
      citations: [
        {
          citation_id: "citation-1",
          valid: false,
          evidence_ids: ["evidence-1"],
        },
      ],
      evidence: [{ ...result.evidence?.[0], verified: false }],
    } as ResearchTaskResultResponse;
    render(
      <Providers locale="en">
        <>
          <CitationMarker citationId="citation-1" />
          <EvidencePanel result={unverified} />
        </>
      </Providers>,
    );

    await user.click(screen.getByRole("button", { name: /open citation/i }));
    expect(
      screen.getByText("This citation is unverified."),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /open paper/i }));
    expect(useUiStore.getState().contextTab).toBe("papers");
    expect(useUiStore.getState().selectedObjectId).toBe("paper-1");
  });

  it("explains why legacy results have no evidence panel", () => {
    render(
      <Providers locale="en">
        <EvidencePanel
          result={
            {
              ...result,
              evidence: [],
              citations: [],
              capabilities: {
                supports_evidence: false,
                supports_replay: false,
                supports_structured_papers: false,
              },
            } as ResearchTaskResultResponse
          }
        />
      </Providers>,
    );
    expect(
      screen.getByText(/historical result has no evidence/i),
    ).toBeInTheDocument();
  });
});
