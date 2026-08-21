import { describe, expect, it } from "vitest";

import { normalizePaper } from "@/features/papers/paper-model";

describe("normalizePaper", () => {
  it.each([
    [
      { abstract: "An abstract", pdf_url: "https://example.test/paper.pdf" },
      "full",
    ],
    [
      { abstract: "", pdf_url: "https://example.test/paper.pdf" },
      "full_no_abstract",
    ],
    [{ abstract: "An abstract", pdf_url: "" }, "abstract_only"],
    [{ abstract: "", pdf_url: "" }, "unavailable"],
    [
      { abstract: "", pdf_url: "", full_text_status: "pdf_failed" },
      "pdf_failed",
    ],
  ])("maps backend text metadata to %s", (metadata, expected) => {
    const paper = normalizePaper({
      paper_id: "paper-1",
      title: "A paper",
      source: "semantic_scholar",
      ...metadata,
    });

    expect(paper.fullTextStatus).toBe(expected);
  });

  it("prefers an explicit backend status over local inference", () => {
    const paper = normalizePaper({
      paper_id: "paper-1",
      title: "A paper",
      source: "arxiv",
      abstract: "An abstract",
      pdf_url: "https://example.test/paper.pdf",
      full_text_status: "pdf_failed",
    });

    expect(paper.fullTextStatus).toBe("pdf_failed");
  });
});
